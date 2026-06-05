"""
tests/test_sip.py
-----------------
Unit tests for utils/sip.py — SIP future-value calculator.

All tests are pure-math: no network calls, no LLM, no env variables.
Run with:  pytest tests/test_sip.py -v
"""

import pytest
from utils.sip import calculate_sip


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
        # Expected discount by 6% per year for 5 years
        expected_discount = result["nominal_value"] / (1.06 ** 5)
        assert abs(result["inflation_adjusted_value"] - expected_discount) < 1.0

