"""
tests/test_tax.py
-----------------
Unit tests for utils/tax.py — Indian income tax calculator.

Tests cover both New Regime and Old Regime slabs, the 87A rebate,
the 4% education cess, and edge cases like zero income and very
high incomes crossing the 15 lakh slab boundary.

Run with:  pytest tests/test_tax.py -v
"""

import pytest
from utils.tax import calculate_tax


class TestCalculateTax:
    """Tests for the Indian income-tax calculator."""

    # ── Helper ────────────────────────────────────────────
    @staticmethod
    def _new(income):
        return calculate_tax(income)["new_regime"]["total_tax"]

    @staticmethod
    def _old(income):
        return calculate_tax(income)["old_regime"]["total_tax"]

    # ── Zero / very low income ──────────────────────────
    def test_zero_income_no_tax(self):
        result = calculate_tax(0)
        assert result["new_regime"]["total_tax"] == 0.0
        assert result["old_regime"]["total_tax"] == 0.0

    def test_income_below_new_regime_exemption_no_tax(self):
        """New regime: income ≤ 7 lakh after standard deduction → 0 tax (87A rebate)."""
        assert self._new(700000) == 0.0

    def test_income_below_old_regime_exemption_no_tax(self):
        """Old regime: taxable income ≤ 5 lakh → 0 tax (87A rebate)."""
        assert self._old(550000) == 0.0

    # ── Cess is always applied ──────────────────────────
    def test_cess_is_4_percent_of_base_tax(self):
        """Cess should be exactly 4% of base tax for a mid-range income."""
        income = 1_200_000
        result = calculate_tax(income)
        new = result["new_regime"]
        assert round(new["cess"], 2) == round(new["base_tax"] * 0.04, 2)

    # ── Recommendation keys present ─────────────────────
    def test_response_has_required_keys(self):
        keys = {"gross_income", "new_regime", "old_regime", "recommended", "savings"}
        assert keys.issubset(calculate_tax(1_000_000).keys())

    def test_recommended_is_valid_string(self):
        rec = calculate_tax(1_000_000)["recommended"]
        assert rec in ("New Regime", "Old Regime")

    def test_savings_is_non_negative(self):
        assert calculate_tax(800_000)["savings"] >= 0

    # ── High income slab ────────────────────────────────
    def test_high_income_above_15L_charged_30_percent_slab(self):
        """Income > 15L should trigger 30% slab; tax must be > 0 in both regimes."""
        result = calculate_tax(2_000_000)
        assert result["new_regime"]["total_tax"] > 0
        assert result["old_regime"]["total_tax"] > 0

    # ── Standard deductions ─────────────────────────────
    def test_new_regime_standard_deduction_is_75k(self):
        assert calculate_tax(1_000_000)["new_regime"]["standard_deduction"] == 75000

    def test_old_regime_standard_deduction_is_50k(self):
        assert calculate_tax(1_000_000)["old_regime"]["standard_deduction"] == 50000

    # ── Parametrize ─────────────────────────────────────
    @pytest.mark.parametrize("income", [300_000, 600_000, 900_000, 1_200_000, 1_800_000])
    def test_total_tax_is_non_negative(self, income):
        result = calculate_tax(income)
        assert result["new_regime"]["total_tax"] >= 0
        assert result["old_regime"]["total_tax"] >= 0

    # ── Deductions ──────────────────────────────────────
    def test_old_regime_deductions_applied(self):
        """Old regime: applying deductions should reduce taxable income and total tax."""
        no_deductions = calculate_tax(1000000)
        with_deductions = calculate_tax(1000000, deductions_80c=150000, deductions_80d=25000, hra=50000)
        
        assert with_deductions["old_regime"]["deductions_80c_applied"] == 150000.0
        assert with_deductions["old_regime"]["deductions_80d_applied"] == 25000.0
        assert with_deductions["old_regime"]["hra_applied"] == 50000.0
        assert with_deductions["old_regime"]["total_deductions"] == 50000 + 150000 + 25000 + 50000
        assert with_deductions["old_regime"]["total_tax"] < no_deductions["old_regime"]["total_tax"]

    def test_deductions_caps(self):
        """Deductions should be capped to their maximum allowed limits (1.5L for 80C, 25k for 80D)."""
        result = calculate_tax(1000000, deductions_80c=200000, deductions_80d=40000)
        assert result["old_regime"]["deductions_80c_applied"] == 150000.0
        assert result["old_regime"]["deductions_80d_applied"] == 25000.0

