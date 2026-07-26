"""
tests/test_money_score.py
--------------------------
Unit tests for utils/money_score.py — financial health scoring.

The score is composed of four weighted components:
  Savings rate  (max 30)
  Investment rate (max 25)
  Debt ratio    (max 25)
  Emergency fund coverage (max 20)
  Total max = 100

Run with:  pytest tests/test_money_score.py -v
"""

import pytest
from utils.money_score import calculate_money_score
from app import calcScore


class TestCalculateMoneyScore:
    """Tests for the composite money-health scorer."""

    def test_perfect_score_conditions(self):
        """
        Savings ≥ 30%, Investment ≥ 20%, Debt ≤ 20%, Emergency ≥ 6 months
        → score must be 100.
        """
        score = calculate_money_score(
            income=100_000,
            expenses=10_000,
            savings=35_000,
            investments=25_000,
            debt=10_000,     # 10% of income
            emergency_fund=70_000,  # 7 months of expenses
        )
        assert score == 100

    def test_worst_case_produces_low_score(self):
        """No savings, no investments, heavy debt, zero emergency → low score."""
        score = calculate_money_score(
            income=100_000,
            expenses=90_000,
            savings=0,
            investments=0,
            debt=80_000,
            emergency_fund=0,
        )
        assert score < 40

    def test_score_is_bounded_0_to_100(self):
        """Score must never go below 0 or above 100."""
        for income in [0, 1, 50_000, 1_000_000]:
            score = calculate_money_score(
                income=income,
                expenses=max(1, income * 0.5),
                savings=income * 0.1,
                investments=income * 0.05,
                debt=income * 0.3,
                emergency_fund=income * 0.2,
            )
            assert 0 <= score <= 100

    def test_zero_income_does_not_raise(self):
        """Division by zero safeguard: income=0 must not crash."""
        score = calculate_money_score(
            income=0, expenses=0, savings=0, investments=0, debt=0, emergency_fund=0
        )
        assert isinstance(score, int)

    def test_zero_expenses_with_emergency_fund(self):
        """Emergency coverage with zero expenses should not crash (special case)."""
        score = calculate_money_score(
            income=50_000, expenses=0, savings=15_000,
            investments=10_000, debt=5_000, emergency_fund=50_000
        )
        assert score > 0

    def test_returns_integer(self):
        result = calculate_money_score(100_000, 30_000, 20_000, 15_000, 10_000, 60_000)
        assert isinstance(result, int)

    @pytest.mark.parametrize("savings_rate,expected_min_addition", [
        (0.35, 30),   # ≥ 30% → full 30 pts
        (0.22, 20),   # ≥ 20% → 20 pts
        (0.05, 10),   # < 20% → 10 pts
    ])
    def test_savings_component_tiers(self, savings_rate, expected_min_addition):
        """Verify savings component grants correct tier points."""
        income = 100_000
        savings = income * savings_rate
        # Set other components to a consistent baseline
        score = calculate_money_score(income, 10_000, savings, 0, 0, 0)
        # Savings component alone should provide at least expected points
        # (score = savings_component + min points from other dims)
        assert score >= expected_min_addition


def test_money_score_normal():
    result = calcScore(income=80000, expenses=40000, savings=20000, invest=500000, debt=100000, emergency=240000)
    assert "score" in result

def test_money_score_zero_income():
    result = calcScore(income=0, expenses=0, savings=0, invest=0, debt=0, emergency=0)
    assert result["score"] == 0

def test_money_score_high_debt():
    result = calcScore(income=100000, expenses=50000, savings=10000, invest=200000, debt=1000000, emergency=50000)
    assert result["score"] < 50