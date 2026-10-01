import math
import numpy as np
from typing import List, Dict, Any, Union, Tuple

# --- Constants & Assumptions ---
RISK_FREE_RATE = 0.06

ASSET_CLASSES = ["equity", "debt", "gold", "real_estate", "cash", "crypto"]

EXPECTED_RETURNS = np.array([0.12, 0.07, 0.08, 0.09, 0.04, 0.20])

ANNUAL_VOLATILITY = np.array([0.18, 0.04, 0.14, 0.10, 0.005, 0.60])

CORRELATION_MATRIX = np.array([
    [1.00, 0.10, 0.05, 0.50, 0.00, 0.30],
    [0.10, 1.00, 0.20, 0.20, 0.30, 0.00],
    [0.05, 0.20, 1.00, 0.10, 0.10, 0.10],
    [0.50, 0.20, 0.10, 1.00, 0.00, 0.15],
    [0.00, 0.30, 0.10, 0.00, 1.00, 0.00],
    [0.30, 0.00, 0.10, 0.15, 0.00, 1.00]
])

CONCENTRATION_THRESHOLDS = {
    "single_holding": 0.25,
    "single_class": 0.60,
    "top_three": 0.75
}

SCENARIOS = [
    {"name": "equity_crash", "shocks": np.array([-0.30, 0.02, 0.08, -0.12, 0.00, -0.50])},
    {"name": "rate_hike", "shocks": np.array([-0.08, -0.06, -0.03, -0.10, 0.01, -0.15])},
    {"name": "inflation_spike", "shocks": np.array([-0.10, -0.07, 0.12, 0.03, -0.04, -0.10])},
    {"name": "bull_run", "shocks": np.array([0.25, 0.03, -0.02, 0.10, 0.00, 0.60])}
]

CATEGORY_ALIASES = {
    "stock": "equity", "stocks": "equity", "equity": "equity", "equities": "equity",
    "mutual fund": "equity", "etf": "equity", "index fund": "equity",
    "bond": "debt", "bonds": "debt", "debt": "debt", "fixed income": "debt", "fd": "debt", "ppf": "debt", "epf": "debt",
    "gold": "gold", "sgb": "gold", "gold etf": "gold",
    "real estate": "real_estate", "property": "real_estate", "reit": "real_estate", "real_estate": "real_estate",
    "cash": "cash", "savings": "cash", "liquid": "cash",
    "crypto": "crypto", "cryptocurrency": "crypto", "bitcoin": "crypto"
}


def normalize_holdings(holdings: List[Dict[str, Any]]) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """Validate and normalize portfolio holdings into internal format."""
    if not isinstance(holdings, list) or not holdings:
        return {"error": "Holdings must be a non-empty list."}

    if len(holdings) > 100:
        return {"error": "Maximum 100 holdings allowed."}

    normalized = []
    for h in holdings:
        if not isinstance(h, dict):
            return {"error": "Each holding must be a dictionary."}
        if "name" not in h or "amount" not in h or "category" not in h:
            return {"error": "Missing required keys: name, amount, category."}

        name = h["name"]
        if not isinstance(name, str) or not name.strip():
            return {"error": "Name must be a non-empty string."}

        amount = h["amount"]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            return {"error": f"Amount for {name} must be a number."}
        if not math.isfinite(amount) or amount <= 0:
            return {"error": f"Amount for {name} must be a finite positive number."}

        category = h["category"]
        if not isinstance(category, str):
            return {"error": f"Category for {name} must be a string."}

        cat_clean = category.strip().lower()
        if cat_clean not in CATEGORY_ALIASES:
            return {"error": f"Unknown category for {name}: {category}"}

        normalized.append({
            "name": name.strip(),
            "amount": float(amount),
            "category": category,
            "asset_class": CATEGORY_ALIASES[cat_clean]
        })

    return normalized


def compute_weights(holdings: List[Dict[str, Any]]) -> Tuple[List[float], np.ndarray]:
    """Compute normalized weights for individual holdings and aggregate asset classes."""
    total = sum(h["amount"] for h in holdings)
    holding_weights = [h["amount"] / total for h in holdings]

    class_totals = {c: 0.0 for c in ASSET_CLASSES}
    for h in holdings:
        class_totals[h["asset_class"]] += h["amount"]

    class_weights = np.array([class_totals[c] / total for c in ASSET_CLASSES])
    return holding_weights, class_weights


def expected_return(class_weights: np.ndarray) -> float:
    """Calculate the expected annual return based on class weights."""
    return float(np.dot(class_weights, EXPECTED_RETURNS))


def portfolio_volatility(class_weights: np.ndarray) -> float:
    """Calculate portfolio volatility using the covariance matrix."""
    diag_vol = np.diag(ANNUAL_VOLATILITY)
    sigma = diag_vol @ CORRELATION_MATRIX @ diag_vol
    return float(math.sqrt(class_weights.T @ sigma @ class_weights))


def sharpe_ratio(ret: float, vol: float) -> float:
    """Calculate the Sharpe ratio."""
    if vol == 0.0:
        return 0.0
    return (ret - RISK_FREE_RATE) / vol


def average_correlation(class_weights: np.ndarray) -> float:
    """Calculate weighted average pairwise correlation across held classes."""
    held_idx = np.where(class_weights > 0)[0]
    if len(held_idx) <= 1:
        return 0.0

    total_corr = 0.0
    weight_sum = 0.0
    for i in range(len(held_idx)):
        for j in range(i + 1, len(held_idx)):
            idx_i = held_idx[i]
            idx_j = held_idx[j]
            w_prod = class_weights[idx_i] * class_weights[idx_j]
            total_corr += w_prod * CORRELATION_MATRIX[idx_i, idx_j]
            weight_sum += w_prod

    if weight_sum == 0.0:
        return 0.0
    return float(total_corr / weight_sum)


def risk_score(vol: float) -> float:
    """Calculate normalized risk score from 0 to 100."""
    return round(min(100.0, (vol / 0.30) * 100), 1)


def risk_label(vol: float) -> str:
    """Determine risk label based on portfolio volatility."""
    if vol < 0.08:
        return "Low"
    elif vol < 0.15:
        return "Moderate"
    return "High"


def diversification_score(holding_weights: List[float], class_weights: np.ndarray) -> float:
    """Calculate a score from 0 to 100 evaluating portfolio diversification."""
    if len(holding_weights) == 1:
        return 0.0

    sum_w_h_sq = sum(w**2 for w in holding_weights)
    holding_spread = min(1.0, (1.0 / sum_w_h_sq - 1.0) / 9.0) if sum_w_h_sq > 0 else 0.0

    sum_w_c_sq = float(np.sum(class_weights**2))
    class_spread = min(1.0, (1.0 / sum_w_c_sq - 1.0) / 5.0) if sum_w_c_sq > 0 else 0.0

    vol = portfolio_volatility(class_weights)
    weighted_vol_sum = float(np.dot(class_weights, ANNUAL_VOLATILITY))

    if vol == 0.0:
        dr = 1.0
    else:
        dr = weighted_vol_sum / vol

    correlation_benefit = min(1.0, max(0.0, (dr - 1.0) / 0.5))

    score = 100.0 * (0.4 * holding_spread + 0.3 * class_spread + 0.3 * correlation_benefit)
    return round(score, 1)


def detect_concentration(
    holding_weights: List[float],
    class_weights: np.ndarray,
    holdings: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Identify concentration risks in holdings and asset classes."""
    flags = []

    # Check individual holdings
    for i, w in enumerate(holding_weights):
        if w > CONCENTRATION_THRESHOLDS["single_holding"]:
            subject = holdings[i]["name"] if holdings else f"Holding {i}"
            flags.append({
                "type": "single_holding",
                "subject": subject,
                "weight_percent": round(w * 100, 2),
                "threshold_percent": round(CONCENTRATION_THRESHOLDS["single_holding"] * 100, 2),
                "message": f"High concentration in single holding: {subject}"
            })

    # Check top three combined
    if len(holding_weights) > 3:
        top_three = sorted(enumerate(holding_weights), key=lambda x: x[1], reverse=True)[:3]
        top_three_weight = sum(w for _, w in top_three)
        if top_three_weight > CONCENTRATION_THRESHOLDS["top_three"]:
            if holdings:
                subject = ", ".join(holdings[i]["name"] for i, _ in top_three)
            else:
                subject = ", ".join(f"Holding {i}" for i, _ in top_three)

            flags.append({
                "type": "top_three",
                "subject": subject,
                "weight_percent": round(top_three_weight * 100, 2),
                "threshold_percent": round(CONCENTRATION_THRESHOLDS["top_three"] * 100, 2),
                "message": f"High concentration in top 3 holdings: {subject}"
            })

    # Check asset classes
    for i, w in enumerate(class_weights):
        if w > CONCENTRATION_THRESHOLDS["single_class"]:
            flags.append({
                "type": "single_class",
                "subject": ASSET_CLASSES[i],
                "weight_percent": round(w * 100, 2),
                "threshold_percent": round(CONCENTRATION_THRESHOLDS["single_class"] * 100, 2),
                "message": f"High concentration in asset class: {ASSET_CLASSES[i]}"
            })

    return flags


def run_scenarios(class_weights: np.ndarray, total_amount: float) -> List[Dict[str, Any]]:
    """Simulate portfolio performance under predefined economic scenarios."""
    results = []
    for scenario in SCENARIOS:
        shocks = scenario["shocks"]
        port_change_pct = float(np.dot(class_weights, shocks))
        port_change_amt = port_change_pct * total_amount

        by_class = {}
        for i, c in enumerate(ASSET_CLASSES):
            if class_weights[i] > 0:
                by_class[c] = round(float(shocks[i] * 100), 2)

        results.append({
            "name": scenario["name"],
            "portfolio_change_percent": round(port_change_pct * 100, 2),
            "portfolio_change_amount": round(port_change_amt, 2),
            "by_class": by_class
        })
    return results


def analyze_portfolio(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform a full risk analysis on the given portfolio holdings."""
    norm_holdings = normalize_holdings(holdings)
    if isinstance(norm_holdings, dict) and "error" in norm_holdings:
        return norm_holdings

    total_amount = sum(h["amount"] for h in norm_holdings)
    holding_weights, class_weights = compute_weights(norm_holdings)

    ret = expected_return(class_weights)
    vol = portfolio_volatility(class_weights)
    sharpe = sharpe_ratio(ret, vol)
    avg_corr = average_correlation(class_weights)
    score = risk_score(vol)
    label = risk_label(vol)
    div_score = diversification_score(holding_weights, class_weights)
    flags = detect_concentration(holding_weights, class_weights, norm_holdings)
    scenarios_out = run_scenarios(class_weights, total_amount)

    weights_dict = {
        "holdings": [
            {"name": norm_holdings[i]["name"], "weight_percent": round(w * 100, 2)}
            for i, w in enumerate(holding_weights)
        ],
        "asset_classes": {ASSET_CLASSES[i]: round(class_weights[i] * 100, 2) for i in range(len(ASSET_CLASSES))}
    }

    assumptions = {
        "RISK_FREE_RATE": RISK_FREE_RATE,
        "ASSET_CLASSES": ASSET_CLASSES,
        "EXPECTED_RETURNS": EXPECTED_RETURNS.tolist(),
        "ANNUAL_VOLATILITY": ANNUAL_VOLATILITY.tolist(),
        "CORRELATION_MATRIX": CORRELATION_MATRIX.tolist(),
        "CONCENTRATION_THRESHOLDS": CONCENTRATION_THRESHOLDS
    }

    return {
        "total_value": round(total_amount, 2),
        "weights": weights_dict,
        "expected_return_percent": round(ret * 100, 2),
        "volatility_percent": round(vol * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "average_correlation": round(avg_corr, 2),
        "risk_score": score,
        "risk_label": label,
        "diversification_score": div_score,
        "concentration_flags": flags,
        "scenarios": scenarios_out,
        "assumptions": assumptions,
        "disclaimer": "Educational analysis based on fixed assumptions. Not financial advice."
    }
