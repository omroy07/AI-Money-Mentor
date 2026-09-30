"""
tests/test_goal_planner.py
---------------------------
Unit tests for utils/sip.py — Goal-Based Savings Planner (reverse SIP).

All tests are pure-math: no network calls, no LLM, no env variables.
Run with:  pytest tests/test_goal_planner.py -v
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from utils.goal_explainer import build_goal_prompt, explain_goal, render_fallback
from utils.goal_planner import (
    assess_feasibility,
    estimate_time_to_goal,
    generate_alternatives,
    plan_goal,
    required_monthly_savings,
    suggest_budget_adjustments,
)
from utils.sip import calculate_goal_sip, calculate_sip


class TestCalculateGoalSip:
    """Tests for the reverse-SIP (goal -> required monthly investment) formula."""

    def test_zero_rate_splits_goal_evenly(self):
        """At 0% annual rate, monthly SIP is simply goal / months."""
        result = calculate_goal_sip(goal=120000, rate=0, years=1)
        assert result["monthly_sip"] == 10000.0
        assert result["total_invested"] == 120000.0
        assert result["returns"] == 0.0

    def test_positive_rate_requires_less_than_zero_rate(self):
        """A positive return rate should require a smaller monthly SIP than 0%."""
        zero_rate = calculate_goal_sip(goal=1000000, rate=0, years=5)
        positive_rate = calculate_goal_sip(goal=1000000, rate=12, years=5)
        assert positive_rate["monthly_sip"] < zero_rate["monthly_sip"]

    def test_returns_dict_type(self):
        result = calculate_goal_sip(goal=500000, rate=10, years=3)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"monthly_sip", "total_invested", "returns"}

    def test_total_invested_plus_returns_equals_goal(self):
        result = calculate_goal_sip(goal=1000000, rate=12, years=3)
        assert abs((result["total_invested"] + result["returns"]) - 1000000) < 0.01

    def test_round_trip_with_calculate_sip(self):
        """Feeding the resulting monthly SIP back into calculate_sip should
        reproduce (approximately) the original goal amount."""
        goal = 1000000
        rate = 12
        years = 3
        result = calculate_goal_sip(goal=goal, rate=rate, years=years)

        fv = calculate_sip(monthly=result["monthly_sip"], rate=rate, years=years)
        assert abs(fv["nominal_value"] - goal) < 1.0

    @pytest.mark.parametrize("goal,rate,years", [
        (1000000, 12, 3),
        (500000, 8, 5),
        (5000000, 15, 20),
    ])
    def test_monthly_sip_always_positive(self, goal, rate, years):
        result = calculate_goal_sip(goal, rate, years)
        assert result["monthly_sip"] > 0


class TestGoalRecommendationEngine:
    """Tests for utils/goal_planner.py - deterministic financial goal engine."""

    def test_laptop_example_is_stretch(self):
        """Rs.80,000 laptop over 8 months on Rs.35,000 income.

        Rs.10,000/month is ~28.6% of income -> stretch, achievable only if
        expenses leave a surplus of Rs.10,000 or more.
        """
        monthly = required_monthly_savings(target=80000, months=8)
        assert monthly == Decimal("10000.00")

        result = assess_feasibility(required=monthly, income=35000, expenses=25000)
        assert result.status == "stretch"
        assert result.savings_ratio == Decimal("0.29")
        assert result.required_monthly_savings == Decimal("10000.00")

    def test_laptop_example_not_feasible_without_surplus(self):
        """Same laptop goal is not feasible if expenses eat the surplus."""
        monthly = required_monthly_savings(target=80000, months=8)
        result = assess_feasibility(required=monthly, income=35000, expenses=30000)
        assert result.status == "not_feasible"

    def test_easily_feasible_goal(self):
        result = assess_feasibility(required=5000, income=35000, expenses=25000)
        assert result.status == "feasible"

    def test_impossible_goal_ten_lakh_in_3_months(self):
        """Rs.10L in 3 months on Rs.20K income must be not_feasible."""
        monthly = required_monthly_savings(target=1000000, months=3)
        assert monthly == Decimal("333333.33")
        result = assess_feasibility(required=monthly, income=20000)
        assert result.status == "not_feasible"

    def test_estimate_time_to_goal(self):
        assert estimate_time_to_goal(target=80000, monthly_savings=10000) == 8
        assert estimate_time_to_goal(target=80000, monthly_savings=5000) == 16
        # Ceiling behaviour.
        assert estimate_time_to_goal(target=10000, monthly_savings=3000) == 4

    def test_suggest_budget_adjustments_trims_discretionary_first(self):
        adjusted = suggest_budget_adjustments(
            expenses_by_category={
                "dining_out": 5000,
                "entertainment": 3000,
                "rent": 15000,
            },
            gap=6000,
        )
        # dining_out fully trimmed (5000), entertainment partially trimmed (1000).
        assert adjusted["dining_out"] == Decimal("0")
        assert adjusted["entertainment"] == Decimal("2000")
        # Non-discretionary categories are never touched.
        assert "rent" not in adjusted

    def test_generate_alternatives_covers_kinds(self):
        alternatives = generate_alternatives(
            target=80000,
            months=8,
            income=35000,
            extended_months=16,
            reduced_target=56000,
            partial_down_payment=20000,
            cheaper_option_target=48000,
        )
        assert len(alternatives) == 4
        # Extended timeline halves the monthly amount.
        assert alternatives[0].required_monthly_savings == Decimal("5000.00")
        # Reduced target over the same timeline.
        assert alternatives[1].required_monthly_savings == Decimal("7000.00")

    def test_plan_goal_returns_structured_result(self):
        plan = plan_goal(
            target=80000, months=8, income=35000, expenses=25000
        )
        assert plan["required_monthly_savings"] == 10000.0
        assert plan["status"] == "stretch"
        assert plan["months_to_goal"] == 8
        assert plan["available_surplus"] == 10000.0
        assert len(plan["alternatives"]) == 3

    def test_zero_income_raises(self):
        with pytest.raises(ValueError):
            assess_feasibility(required=1000, income=0)

    def test_zero_months_raises(self):
        with pytest.raises(ValueError):
            required_monthly_savings(target=1000, months=0)

    def test_negative_values_raise(self):
        with pytest.raises(ValueError):
            required_monthly_savings(target=-1000, months=8)
        with pytest.raises(ValueError):
            assess_feasibility(required=1000, income=35000, expenses=-500)
        with pytest.raises(ValueError):
            estimate_time_to_goal(target=80000, monthly_savings=-100)

    def test_existing_savings_covering_goal_needs_zero(self):
        assert required_monthly_savings(target=80000, months=8, current_savings=80000) == Decimal("0")
        assert required_monthly_savings(target=80000, months=8, current_savings=90000) == Decimal("0")


class TestGoalExplainer:
    """AI layer must explain, never recalculate; fallback must work."""

    def _stretch_plan(self):
        return plan_goal(target=80000, months=8, income=35000, expenses=25000)

    def test_prompt_says_use_only_supplied_numbers(self):
        prompt = build_goal_prompt(self._stretch_plan())
        assert "Use only the numbers below" in prompt
        assert "Do NOT recalculate" in prompt
        assert "80000" in prompt.replace(",", "")

    def test_mocked_groq_never_changes_numbers(self):
        plan = self._stretch_plan()
        before = (plan["required_monthly_savings"], plan["status"])

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Summary: stretch goal needs Rs.10,000/month."))]
        )
        text = explain_goal(plan, client=mock_client)
        assert "stretch" in text.lower()

        # Deterministic numbers are untouched by the AI layer.
        assert (plan["required_monthly_savings"], plan["status"]) == before
        assert plan["required_monthly_savings"] == 10000.0
        mock_client.chat.completions.create.assert_called_once()

    def test_fallback_when_no_client(self):
        text = render_fallback(self._stretch_plan())
        assert "stretch" in text
        assert "10000" in text.replace(",", "")

    def test_fallback_on_groq_error(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("timeout")
        text = explain_goal(self._stretch_plan(), client=mock_client)
        assert "stretch" in text
        assert "10000" in text.replace(",", "")


class TestFeasibilityRefinement:
    """Surplus is the hard achievability gate; ratio grades comfort.

    - required > surplus -> achievable=False, status="not_feasible"
    - required <= surplus -> achievable=True; ratio decides feasible/stretch
    - ratio > 40% but covered -> achievable=True, "stretch" flagged aggressive
    """

    def test_required_equals_available_above_40pct_is_achievable(self):
        """Boundary: income 30k, expenses 10k, goal 20k over 1 month.

        Required (20k) == available (20k) at a 67% ratio: achievable,
        but aggressive stretch - never not_feasible.
        """
        monthly = required_monthly_savings(target=20000, months=1)
        assert monthly == Decimal("20000.00")
        result = assess_feasibility(required=monthly, income=30000, expenses=10000)
        assert result.achievable is True
        assert result.status != "not_feasible"
        assert result.status == "stretch"
        assert "aggressive" in result.message.lower()

    def test_required_above_available_is_not_achievable(self):
        result = assess_feasibility(required=10000, income=35000, expenses=30000)
        assert result.achievable is False
        assert result.status == "not_feasible"

    def test_ratio_up_to_20pct_is_feasible(self):
        result = assess_feasibility(required=5000, income=35000, expenses=25000)
        assert result.achievable is True
        assert result.status == "feasible"

    def test_ratio_20_to_40pct_is_stretch(self):
        result = assess_feasibility(required=10000, income=35000, expenses=25000)
        assert result.achievable is True
        assert result.status == "stretch"

    def test_ratio_above_40pct_covered_is_aggressive_stretch(self):
        result = assess_feasibility(required=20000, income=30000, expenses=10000)
        assert result.achievable is True
        assert result.status == "stretch"
        assert "aggressive" in result.message.lower()

    def test_ratio_above_40pct_unknown_surplus_stays_not_feasible(self):
        """Surplus unknown (no expenses): ratio rule alone decides (preserved)."""
        result = assess_feasibility(required=Decimal("333333.33"), income=20000)
        assert result.achievable is False
        assert result.status == "not_feasible"

    def test_plan_goal_exposes_achievable(self):
        covered = plan_goal(target=20000, months=1, income=30000, expenses=10000)
        assert covered["achievable"] is True
        assert covered["status"] == "stretch"

        shortfall = plan_goal(target=80000, months=8, income=35000, expenses=30000)
        assert shortfall["achievable"] is False
        assert shortfall["status"] == "not_feasible"

    def test_result_to_dict_includes_achievable(self):
        result = assess_feasibility(required=10000, income=35000, expenses=25000)
        assert result.to_dict()["achievable"] is True
