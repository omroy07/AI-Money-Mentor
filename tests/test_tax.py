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

    def test_custom_deductions_applied_old_regime(self):
        result = calculate_tax(1000000, deduction_80c=100000, deduction_80d=20000, deduction_hra=30000)
        assert result["deductions_applied"]["80c"] == 100000
        assert result["deductions_applied"]["80d"] == 20000
        assert result["deductions_applied"]["hra"] == 30000
        # Total deductions = 50k (std) + 100k + 20k + 30k = 200k
        assert result["deductions_applied"]["total"] == 200000
        # Taxable income = 1M - 200k = 800k
        assert result["old_regime"]["taxable_income"] == 800000

    # ── HRA Exemption Engine ───────────────────────────
    def test_calculate_hra_exemption_metro(self):
        from utils.tax import calculate_hra_exemption
        # Basic: 600,000, Rent: 180,000, HRA Received: 240,000, Metro: True
        # Tier 1: 240,000
        # Tier 2: 180,000 - 10% of 600,000 = 120,000
        # Tier 3: 50% of 600,000 = 300,000
        # Expected: min(240k, 120k, 300k) = 120,000
        res = calculate_hra_exemption(600000, 180000, 240000, True)
        assert res["actual_hra"] == 240000.0
        assert res["rent_minus_10_percent_basic"] == 120000.0
        assert res["salary_percentage_limit"] == 300000.0
        assert res["calculated_exemption"] == 120000.0

    def test_calculate_hra_exemption_non_metro(self):
        from utils.tax import calculate_hra_exemption
        # Basic: 600,000, Rent: 180,000, HRA Received: 240,000, Metro: False
        # Tier 3: 40% of 600,000 = 240,000
        res = calculate_hra_exemption(600000, 180000, 240000, False)
        assert res["salary_percentage_limit"] == 240000.0
        assert res["calculated_exemption"] == 120000.0

    def test_calculate_hra_exemption_rent_less_than_10_percent_basic(self):
        from utils.tax import calculate_hra_exemption
        # Basic: 600,000, Rent: 50,000, HRA Received: 100,000, Metro: True
        # Tier 2: 50,000 - 60,000 = -10,000 -> max(0, -10k) = 0
        res = calculate_hra_exemption(600000, 50000, 100000, True)
        assert res["rent_minus_10_percent_basic"] == 0.0
        assert res["calculated_exemption"] == 0.0

    def test_calculate_tax_integration_with_hra_inputs(self):
        hra_inputs = {
            "basic_salary": 600000.0,
            "rent_paid": 180000.0,
            "hra_received": 240000.0,
            "is_metro": True
        }
        result = calculate_tax(1000000, deduction_80c=100000, deduction_80d=20000, hra_inputs=hra_inputs)
        # HRA Exemption should be 120k
        assert result["deductions_applied"]["hra"] == 120000.0
        # Total deductions = 50k (std) + 100k + 20k + 120k = 290k
        assert result["deductions_applied"]["total"] == 290000.0
        assert result["hra_exemption_details"]["calculated_exemption"] == 120000.0

    def test_simulate_tax_scenarios_integration_with_hra_inputs(self):
        from utils.tax import simulate_tax_scenarios
        scenario_a = {
            "deduction_80c": 100000.0,
            "deduction_80d": 20000.0,
            "hra_inputs": {
                "basic_salary": 600000.0,
                "rent_paid": 180000.0,
                "hra_received": 240000.0,
                "is_metro": True
            }
        }
        scenario_b = {
            "deduction_80c": 150000.0,
            "deduction_80d": 25000.0,
            "hra_inputs": {
                "basic_salary": 600000.0,
                "rent_paid": 200000.0,
                "hra_received": 240000.0,
                "is_metro": True
            }
        }
        res = simulate_tax_scenarios(1200000, scenario_a, scenario_b)
        assert res["scenario_a"]["deductions_applied"]["hra"] == 120000.0
        assert res["scenario_b"]["deductions_applied"]["hra"] == 140000.0


class TestTaxRegimeComparator:
    """Unit tests for Old vs New tax regime side-by-side comparator and recommendation."""

    def test_side_by_side_regime_comparison_structure(self):
        """Calculator returns complete side-by-side details for both Old and New regimes."""
        result = calculate_tax(1200000, deduction_80c=150000, deduction_80d=25000, deduction_hra=60000)
        
        # Verify both regimes have all required comparison attributes
        for regime in ("new_regime", "old_regime"):
            assert regime in result
            details = result[regime]
            for key in ("standard_deduction", "taxable_income", "base_tax", "cess", "surcharge", "total_tax"):
                assert key in details
                assert isinstance(details[key], (int, float))

        # Verify deductions breakdown
        assert "deductions_applied" in result
        assert result["deductions_applied"]["80c"] == 150000.0
        assert result["deductions_applied"]["80d"] == 25000.0
        assert result["deductions_applied"]["hra"] == 60000.0
        assert result["deductions_applied"]["total"] == 50000 + 150000 + 25000 + 60000

        # Recommendation and savings
        assert result["recommended"] in ("New Regime", "Old Regime")
        assert result["savings"] >= 0

    def test_recommends_new_regime_when_zero_deductions(self):
        """When user has no 80C/80D/HRA deductions, New Regime provides lower tax and is recommended."""
        # At 15 Lakhs income:
        # New Regime standard deduction is 75,000, Old Regime standard deduction is 50,000
        # New regime has wider slabs and lower rates
        result = calculate_tax(1500000, deduction_80c=0, deduction_80d=0, deduction_hra=0)
        assert result["new_regime"]["total_tax"] < result["old_regime"]["total_tax"]
        assert result["recommended"] == "New Regime"
        assert result["savings"] == round(result["old_regime"]["total_tax"] - result["new_regime"]["total_tax"], 2)

    def test_recommends_old_regime_when_deductions_are_high(self):
        """When user has high deductions, Old Regime becomes cheaper and is recommended."""
        # Income 13L with high HRA and 80C/80D brings Old taxable income under 5L (zero tax)
        # while New Regime has taxable income 12.25L with 26,000 tax
        result = calculate_tax(1300000, deduction_80c=150000, deduction_80d=25000, deduction_hra=650000)
        assert result["old_regime"]["total_tax"] < result["new_regime"]["total_tax"]
        assert result["recommended"] == "Old Regime"
        assert result["savings"] == round(result["new_regime"]["total_tax"] - result["old_regime"]["total_tax"], 2)

    def test_section_80c_deduction_capped_at_150000(self):
        """Section 80C deduction must be capped at statutory ₹1,50,000 limit."""
        result = calculate_tax(1000000, deduction_80c=250000)
        assert result["deductions_applied"]["80c"] == 150000.0
        # Total = 50k (std) + 150k (80c) = 200k
        assert result["old_regime"]["taxable_income"] == 800000.0

    def test_section_80d_deduction_capped_at_25000(self):
        """Section 80D deduction must be capped at statutory ₹25,000 standard limit."""
        result = calculate_tax(1000000, deduction_80d=60000)
        assert result["deductions_applied"]["80d"] == 25000.0
        # Total = 50k (std) + 25k (80d) = 75k
        assert result["old_regime"]["taxable_income"] == 925000.0

    def test_new_regime_disallows_80c_80d_and_hra(self):
        """New Regime does not allow 80C, 80D or HRA deductions; only ₹75,000 standard deduction applies."""
        result_with_deductions = calculate_tax(1200000, deduction_80c=150000, deduction_80d=25000, deduction_hra=80000)
        result_without_deductions = calculate_tax(1200000, deduction_80c=0, deduction_80d=0, deduction_hra=0)
        
        # New regime taxable income and total tax must remain identical regardless of 80C/80D/HRA
        assert result_with_deductions["new_regime"]["taxable_income"] == result_without_deductions["new_regime"]["taxable_income"]
        assert result_with_deductions["new_regime"]["total_tax"] == result_without_deductions["new_regime"]["total_tax"]
        assert result_with_deductions["new_regime"]["standard_deduction"] == 75000.0

    def test_savings_strictly_equals_difference(self):
        """Savings field is always exact absolute difference between New and Old regime tax."""
        for income in (700000, 1000000, 1500000, 2500000):
            res = calculate_tax(income, deduction_80c=120000, deduction_80d=20000, deduction_hra=50000)
            expected_savings = round(abs(res["old_regime"]["total_tax"] - res["new_regime"]["total_tax"]), 2)
            assert res["savings"] == expected_savings

    def test_equal_tax_liability_zero_tax(self):
        """When income is zero or below rebate thresholds for both regimes, both taxes are 0 and savings is 0."""
        res = calculate_tax(300000)
        assert res["new_regime"]["total_tax"] == 0.0
        assert res["old_regime"]["total_tax"] == 0.0
        assert res["savings"] == 0.0
        assert res["is_equal"] is True

    def test_negative_inputs_clamped(self):
        """Negative inputs are clamped to zero and do not corrupt calculation."""
        res = calculate_tax(-100000, deduction_80c=-50000, deduction_80d=-10000, deduction_hra=-20000)
        assert res["gross_income"] == 0.0
        assert res["new_regime"]["total_tax"] == 0.0
        assert res["old_regime"]["total_tax"] == 0.0

    def test_tax_route_post_returns_comparator_data(self):
        """Flask route POST /tax accepts income and deductions and returns comparator results."""
        from app import app
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["TESTING"] = True
        client = app.test_client()
        response = client.post("/tax", json={
            "income": 1200000,
            "deduction_80c": 150000,
            "deduction_80d": 25000,
            "deduction_hra": 50000
        })
        assert response.status_code == 200
        data = response.get_json()
        assert "tax" in data
        tax_res = data["tax"]
        assert "new_regime" in tax_res
        assert "old_regime" in tax_res
        assert "recommended" in tax_res
        assert "savings" in tax_res
        assert tax_res["gross_income"] == 1200000
        assert tax_res["deductions_applied"]["80c"] == 150000
        assert tax_res["deductions_applied"]["80d"] == 25000
        assert tax_res["deductions_applied"]["hra"] == 50000

    def test_tax_route_post_validation(self):
        """Flask route POST /tax returns 400 on negative or invalid income."""
        from app import app
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["TESTING"] = True
        client = app.test_client()
        response = client.post("/tax", json={"income": -500})
        assert response.status_code == 400


