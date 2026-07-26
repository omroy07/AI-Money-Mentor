"""
tests/test_sip.py
-----------------
Unit tests for utils/sip.py — SIP future-value calculator.

All tests are pure-math: no network calls, no LLM, no env variables.
Run with:  pytest tests/test_sip.py -v
"""

import pytest
from utils.sip import calculate_sip, calculate_stepup_sip
from app import calcSIP


class TestCalculateSip:
    """Tests for the SIP compound-interest formula."""

    def test_zero_rate_returns_simple_sum(self):
        """At 0% annual rate the future value equals monthly * months."""
        result = calculate_sip(monthly=1000, rate=0, years=5)
        assert result["nominal_value"] == 1000 * 5 * 12

    def test_positive_rate_exceeds_simple_sum(self):
        """With a positive return rate the FV must be greater than simple sum."""
        simple = 5000 * 10 * 12
        result = calculate_sip(monthly=5000, rate=12, years=10)
        assert result["nominal_value"] > simple

    def test_known_value_within_tolerance(self):
        """
        Standard SIP formula verification:
        ₹1,000/month @ 12% p.a. for 1 year ≈ ₹12,809.
        Tolerance: ±1 rupee (rounding).
        """
        result = calculate_sip(monthly=1000, rate=12, years=1)
        assert abs(result["nominal_value"] - 12809.0) < 2.0

    def test_high_investment_scales_linearly(self):
        """Doubling monthly contribution should double the FV."""
        fv_1 = calculate_sip(monthly=5000, rate=10, years=5)["nominal_value"]
        fv_2 = calculate_sip(monthly=10000, rate=10, years=5)["nominal_value"]
        assert abs(fv_2 - 2 * fv_1) < 1.0   # floating-point epsilon

    def test_returns_dict_type(self):
        result = calculate_sip(monthly=2000, rate=8, years=3)
        assert isinstance(result, dict)
        assert "nominal_value" in result
        assert "inflation_adjusted_value" in result

    def test_single_month(self):
        """1 year = 12 months; result must be a finite positive number."""
        result = calculate_sip(monthly=500, rate=6, years=1)
        assert result["nominal_value"] > 0

    @pytest.mark.parametrize("monthly,rate,years", [
        (1000, 12, 10),
        (500, 8, 5),
        (10000, 15, 20),
    ])
    def test_result_always_positive(self, monthly, rate, years):
        assert calculate_sip(monthly, rate, years)["nominal_value"] > 0

    def test_inflation_adjusted_sip(self):
        result = calculate_sip(monthly=1000, rate=12, years=5, inflation_rate=6.0)
        # Without inflation nominal value is > inflation_adjusted_value
        assert result["nominal_value"] > result["inflation_adjusted_value"]
        # Expected discount by 6% per year compounded monthly for 5 years (60 months)
        m = 0.06 / 12
        expected_discount = result["nominal_value"] / ((1 + m) ** 60)
        assert abs(result["inflation_adjusted_value"] - expected_discount) < 1.0


class TestCalculateStepupSip:

    def test_matches_flat_sip_when_stepup_value_is_zero_percentage(self):
        """A 0% step-up should produce identical numbers to a flat SIP."""
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=5,
            stepup_type="percentage", stepup_value=0
        )
        flat = calculate_sip(monthly=5000, rate=12, years=5)
        assert result["stepup_nominal_value"] == result["flat_nominal_value"]
        assert result["flat_nominal_value"] == flat["nominal_value"]

    def test_matches_flat_sip_when_stepup_value_is_zero_amount(self):
        """A Rs 0 step-up should also produce identical numbers to flat SIP."""
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=5,
            stepup_type="amount", stepup_value=0
        )
        assert result["stepup_nominal_value"] == result["flat_nominal_value"]

    def test_flat_value_matches_existing_calculate_sip(self):
        """The flat-SIP branch of this function must agree with calculate_sip
        exactly, since the frontend chart plots both lines and they must be
        consistent with the standalone /sip endpoint."""
        result = calculate_stepup_sip(
            monthly=10000, rate=10, years=10,
            stepup_type="percentage", stepup_value=10
        )
        flat = calculate_sip(monthly=10000, rate=10, years=10)
        assert result["flat_nominal_value"] == flat["nominal_value"]

    def test_percentage_stepup_grows_more_than_flat(self):
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=10,
            stepup_type="percentage", stepup_value=10
        )
        assert result["stepup_nominal_value"] > result["flat_nominal_value"]
        assert result["stepup_total_invested"] > result["flat_total_invested"]

    def test_amount_stepup_grows_more_than_flat(self):
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=10,
            stepup_type="amount", stepup_value=1000
        )
        assert result["stepup_nominal_value"] > result["flat_nominal_value"]

    def test_invalid_stepup_type_raises(self):
        with pytest.raises(ValueError):
            calculate_stepup_sip(
                monthly=5000, rate=12, years=5,
                stepup_type="bogus", stepup_value=10
            )

    def test_single_year_stepup_equals_flat(self):
        """With only 1 year, the step-up never triggers (it only applies
        after month 12), so step-up and flat results must be identical."""
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=1,
            stepup_type="percentage", stepup_value=15
        )
        assert result["stepup_nominal_value"] == result["flat_nominal_value"]

    def test_zero_rate_with_stepup(self):
        """rate=0 must not divide by zero, and step-up still increases
        total invested even with no growth."""
        result = calculate_stepup_sip(
            monthly=5000, rate=0, years=3,
            stepup_type="amount", stepup_value=500
        )
        assert result["stepup_nominal_value"] == result["stepup_total_invested"]
        assert result["stepup_total_invested"] > result["flat_total_invested"]

    def test_yearly_breakdown_length_matches_years(self):
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=7,
            stepup_type="percentage", stepup_value=10
        )
        assert len(result["yearly_breakdown"]) == 7
        assert result["yearly_breakdown"][0]["year"] == 1
        assert result["yearly_breakdown"][-1]["year"] == 7

    def test_yearly_breakdown_values_are_monotonically_increasing(self):
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=5,
            stepup_type="percentage", stepup_value=10
        )
        values = [y["stepup_value"] for y in result["yearly_breakdown"]]
        assert values == sorted(values)
        invested = [y["stepup_invested"] for y in result["yearly_breakdown"]]
        assert invested == sorted(invested)

    def test_inflation_adjustment_applied(self):
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=10,
            stepup_type="percentage", stepup_value=10,
            inflation_rate=6
        )
        assert result["inflation_applied"] == 6
        assert result["stepup_inflation_adjusted_value"] < result["stepup_nominal_value"]
        assert result["flat_inflation_adjusted_value"] < result["flat_nominal_value"]

    def test_no_inflation_means_adjusted_equals_nominal(self):
        result = calculate_stepup_sip(
            monthly=5000, rate=12, years=5,
            stepup_type="amount", stepup_value=500
        )
        assert result["inflation_applied"] == 0.0
        assert result["stepup_inflation_adjusted_value"] == result["stepup_nominal_value"]
        assert result["flat_inflation_adjusted_value"] == result["flat_nominal_value"]


def test_sip_normal():
    result = calcSIP(monthly=10000, rate=12, years=10)
    assert result > 0

def test_sip_zero_input():
    result = calcSIP(monthly=0, rate=12, years=10)
    assert result == 0

def test_sip_edge_case_high_rate():
    result = calcSIP(monthly=5000, rate=50, years=5)
    assert result > 0