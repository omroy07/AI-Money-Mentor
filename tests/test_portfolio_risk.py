import math
import copy
import numpy as np


from utils.portfolio_risk import (
    normalize_holdings,
    compute_weights,
    sharpe_ratio,
    analyze_portfolio,
    CORRELATION_MATRIX
)


def test_validation_empty_list():
    assert "error" in normalize_holdings([])


def test_validation_negative_amount():
    assert "error" in normalize_holdings([{"name": "A", "amount": -100, "category": "equity"}])


def test_validation_zero_amount():
    assert "error" in normalize_holdings([{"name": "A", "amount": 0, "category": "equity"}])


def test_validation_not_a_number():
    assert "error" in normalize_holdings([{"name": "A", "amount": float("nan"), "category": "equity"}])


def test_validation_infinity():
    assert "error" in normalize_holdings([{"name": "A", "amount": float("inf"), "category": "equity"}])


def test_validation_boolean_amount():
    assert "error" in normalize_holdings([{"name": "A", "amount": True, "category": "equity"}])


def test_validation_unknown_category():
    assert "error" in normalize_holdings([{"name": "A", "amount": 100, "category": "unknown_cat"}])


def test_validation_missing_key():
    assert "error" in normalize_holdings([{"name": "A", "amount": 100}])


def test_validation_alias_mapping():
    holdings = [
        {"name": "H1", "amount": 100, "category": "Stocks"},
        {"name": "H2", "amount": 100, "category": "Fixed Income"}
    ]
    norm = normalize_holdings(holdings)
    assert isinstance(norm, list)
    assert norm[0]["asset_class"] == "equity"
    assert norm[1]["asset_class"] == "debt"


def test_validation_more_than_100_holdings():
    holdings = [{"name": f"H{i}", "amount": 10, "category": "cash"} for i in range(101)]
    assert "error" in normalize_holdings(holdings)


def test_weights_sum_to_one():
    holdings = [
        {"name": "H1", "amount": 60, "category": "equity", "asset_class": "equity"},
        {"name": "H2", "amount": 40, "category": "debt", "asset_class": "debt"}
    ]
    h_weights, c_weights = compute_weights(holdings)

    # Expected: holding sum = 1.0, class sum = 1.0
    assert math.isclose(sum(h_weights), 1.0)
    assert math.isclose(np.sum(c_weights), 1.0)


def test_correlation_matrix_properties():
    # Symmetric check
    assert np.allclose(CORRELATION_MATRIX, CORRELATION_MATRIX.T)
    # Ones on diagonal
    assert np.allclose(np.diag(CORRELATION_MATRIX), np.ones(6))
    # All eigenvalues non-negative (Positive Semi-Definite)
    eigenvalues = np.linalg.eigvals(CORRELATION_MATRIX)
    assert np.all(eigenvalues >= -1e-8)


def test_100_percent_cash():
    holdings = [{"name": "Cash", "amount": 1000, "category": "cash"}]
    res = analyze_portfolio(holdings)

    # Expected cash vol is 0.005 -> 0.5%
    # 100% cash volatility = 0.5%
    assert math.isclose(res["volatility_percent"], 0.5, rel_tol=1e-2)
    assert res["risk_label"] == "Low"


def test_100_percent_crypto():
    holdings = [{"name": "BTC", "amount": 1000, "category": "crypto"}]
    res = analyze_portfolio(holdings)

    # Volatility of crypto is 0.60 -> 60%, label High
    # Risk score: min(100, 0.60/0.30 * 100) = 100
    # Diversification: 1 holding -> 0
    assert res["risk_label"] == "High"
    assert math.isclose(res["risk_score"], 100.0)
    assert math.isclose(res["diversification_score"], 0.0)


def test_100_percent_single_equity():
    holdings = [{"name": "AAPL", "amount": 1000, "category": "equity"}]
    res = analyze_portfolio(holdings)

    # Expect single_holding flag and single_class flag
    flags = [f["type"] for f in res["concentration_flags"]]
    assert "single_holding" in flags
    assert "single_class" in flags


def test_balanced_portfolio():
    # Equity 40, Debt 30, Gold 10, Real Estate 10, Cash 10 across 8 holdings, none > 25%
    holdings = [
        {"name": "Eq1", "amount": 20, "category": "equity"},
        {"name": "Eq2", "amount": 20, "category": "equity"},
        {"name": "Debt1", "amount": 15, "category": "debt"},
        {"name": "Debt2", "amount": 15, "category": "debt"},
        {"name": "Gold1", "amount": 10, "category": "gold"},
        {"name": "RE1", "amount": 10, "category": "real estate"},
        {"name": "Cash1", "amount": 5, "category": "cash"},
        {"name": "Cash2", "amount": 5, "category": "cash"}
    ]
    res = analyze_portfolio(holdings)

    # No concentration flags expected
    assert len(res["concentration_flags"]) == 0

    # Diversification score should be > 50
    assert res["diversification_score"] > 50.0

    # Risk label should be Low or Moderate
    assert res["risk_label"] in ["Low", "Moderate"]

    # Hardcoded checks from independent numpy calculation
    assert abs(res["volatility_percent"] - 8.23) < 0.01
    assert abs(res["diversification_score"] - 59.8) < 0.1


def test_balanced_scores_higher_than_concentrated():
    balanced = [
        {"name": "Eq1", "amount": 20, "category": "equity"},
        {"name": "Eq2", "amount": 20, "category": "equity"},
        {"name": "Debt1", "amount": 30, "category": "debt"},
        {"name": "Gold1", "amount": 30, "category": "gold"}
    ]
    concentrated = [
        {"name": "Eq1", "amount": 95, "category": "equity"},
        {"name": "Eq2", "amount": 5, "category": "equity"}
    ]

    res_bal = analyze_portfolio(balanced)
    res_con = analyze_portfolio(concentrated)

    assert res_bal["diversification_score"] > res_con["diversification_score"]


def test_top_three_flag_triggers():
    # Top three sum to > 75%
    holdings = [
        {"name": "H1", "amount": 30, "category": "equity"},
        {"name": "H2", "amount": 30, "category": "equity"},
        {"name": "H3", "amount": 20, "category": "equity"},
        {"name": "H4", "amount": 10, "category": "equity"},
        {"name": "H5", "amount": 10, "category": "equity"}
    ]
    res = analyze_portfolio(holdings)
    flags = [f["type"] for f in res["concentration_flags"]]
    assert "top_three" in flags


def test_two_holdings_no_top_three_flag():
    holdings = [
        {"name": "E", "amount": 50, "category": "equity"},
        {"name": "D", "amount": 50, "category": "debt"}
    ]
    res = analyze_portfolio(holdings)
    flags = [f["type"] for f in res["concentration_flags"]]
    # Should have two single_holding flags, no top_three flag
    assert flags.count("single_holding") == 2
    assert "top_three" not in flags


def test_sharpe_ratio():
    # zero vol -> 0.0
    assert sharpe_ratio(0.10, 0.0) == 0.0

    # 100 percent equity: (0.12 - 0.06) / 0.18 = 0.3333
    res_eq = analyze_portfolio([{"name": "Eq", "amount": 100, "category": "equity"}])
    assert abs(res_eq["sharpe_ratio"] - 0.33) < 0.005

    # 100 percent crypto: (0.20 - 0.06) / 0.60 = 0.2333
    res_crypt = analyze_portfolio([{"name": "Crypt", "amount": 100, "category": "crypto"}])
    assert abs(res_crypt["sharpe_ratio"] - 0.23) < 0.005


def test_scenario_math():
    # 100% equity -> equity_crash is -30%
    holdings1 = [{"name": "Eq", "amount": 100, "category": "equity"}]
    res1 = analyze_portfolio(holdings1)
    crash1 = next(s for s in res1["scenarios"] if s["name"] == "equity_crash")
    # expected: -30%
    assert math.isclose(crash1["portfolio_change_percent"], -30.0)

    # 50% equity, 50% debt
    # shocks: equity_crash for equity = -0.30, debt = 0.02
    # expected: 0.5 * -0.30 + 0.5 * 0.02 = -0.15 + 0.01 = -0.14 -> -14%
    holdings2 = [
        {"name": "Eq", "amount": 50, "category": "equity"},
        {"name": "Debt", "amount": 50, "category": "debt"}
    ]
    res2 = analyze_portfolio(holdings2)
    crash2 = next(s for s in res2["scenarios"] if s["name"] == "equity_crash")
    assert math.isclose(crash2["portfolio_change_percent"], -14.0)


def test_identical_input_gives_identical_output():
    holdings = [
        {"name": "H1", "amount": 60, "category": "equity"},
        {"name": "H2", "amount": 40, "category": "debt"}
    ]
    res1 = analyze_portfolio(copy.deepcopy(holdings))
    res2 = analyze_portfolio(copy.deepcopy(holdings))
    assert res1 == res2


def test_input_list_not_mutated():
    holdings = [{"name": "H1", "amount": 100, "category": "equity"}]
    original = copy.deepcopy(holdings)
    analyze_portfolio(holdings)
    assert holdings == original
