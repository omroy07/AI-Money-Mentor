"""
tests/test_expense_track.py
----------------------------
Unit tests for utils/expense_track.py — expense aggregation logic.

Tests only the pure calculation functions (calculate_expense).
The insights() function requires a live LLM client, so it is
excluded from automated tests here.

Run with:  pytest tests/test_expense_track.py -v
"""

import pytest
from utils.expense_track import calculate_expense


class TestCalculateExpense:
    """Tests for the expense aggregation helper."""

    def test_empty_list_returns_zeros(self):
        result = calculate_expense([])
        assert result["Total"] == 0
        assert result["Average"] == 0
        assert result["By Category"] == {}

    def test_budget_limits_warning(self):
        expenses = [
            {"category": "Food", "amount": 6000.0, "date": "2025-01-01"},
        ]
        result = calculate_expense(expenses)
        assert "Budget Limits" in result
        assert result["Status"]["Food"]["exceeded"] is True
        assert result["Status"]["Food"]["limit"] == 5000.0

    def test_single_expense(self):
        expenses = [{"category": "Food", "amount": 500.0, "date": "2025-01-01"}]
        result = calculate_expense(expenses)
        assert result["Total"] == 500.0
        assert result["Average"] == 500.0
        assert result["By Category"] == {"Food": 500.0}

    def test_multiple_same_category(self):
        expenses = [
            {"category": "Food", "amount": 200.0, "date": "2025-01-01"},
            {"category": "Food", "amount": 300.0, "date": "2025-01-02"},
        ]
        result = calculate_expense(expenses)
        assert result["Total"] == 500.0
        assert result["Average"] == 250.0
        assert result["By Category"]["Food"] == 500.0

    def test_multiple_categories(self):
        expenses = [
            {"category": "Food", "amount": 400.0, "date": "2025-01-01"},
            {"category": "Transport", "amount": 200.0, "date": "2025-01-02"},
            {"category": "Entertainment", "amount": 100.0, "date": "2025-01-03"},
        ]
        result = calculate_expense(expenses)
        assert result["Total"] == 700.0
        assert result["Average"] == pytest.approx(700 / 3, rel=1e-6)
        assert result["By Category"]["Food"] == 400.0
        assert result["By Category"]["Transport"] == 200.0
        assert result["By Category"]["Entertainment"] == 100.0

    def test_total_equals_sum_of_all_amounts(self):
        amounts = [150.5, 320.0, 75.25, 1000.0]
        expenses = [
            {"category": "Test", "amount": a, "date": "2025-01-01"}
            for a in amounts
        ]
        result = calculate_expense(expenses)
        assert result["Total"] == pytest.approx(sum(amounts), rel=1e-9)

    def test_category_totals_sum_to_overall_total(self):
        expenses = [
            {"category": "Rent", "amount": 12000.0, "date": "2025-01-01"},
            {"category": "Food", "amount": 3000.0, "date": "2025-01-02"},
            {"category": "Rent", "amount": 500.0, "date": "2025-01-03"},
        ]
        result = calculate_expense(expenses)
        cat_total = sum(result["By Category"].values())
        assert cat_total == pytest.approx(result["Total"], rel=1e-9)
