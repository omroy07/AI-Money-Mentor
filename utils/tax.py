def calculate_hra_exemption(basic_salary, rent_paid, hra_received, is_metro):
    """
    Calculates the HRA tax exemption under Section 10(13A) of the Income Tax Act.
    Rules:
      1. Actual HRA received.
      2. Rent paid minus 10% of basic salary.
      3. 50% of basic salary (metro cities) or 40% (non-metro cities).
    Returns:
      dict containing the three tiers, calculated exemption, and input parameters.
    """
    basic_salary = float(basic_salary)
    rent_paid = float(rent_paid)
    hra_received = float(hra_received)
    is_metro = bool(is_metro)

    tier1 = hra_received
    tier2 = max(0.0, rent_paid - 0.10 * basic_salary)
    pct = 0.50 if is_metro else 0.40
    tier3 = basic_salary * pct

    exemption = min(tier1, tier2, tier3)
    return {
        "actual_hra": round(tier1, 2),
        "rent_minus_10_percent_basic": round(tier2, 2),
        "salary_percentage_limit": round(tier3, 2),
        "calculated_exemption": round(exemption, 2)
    }


def calculate_tax(income, deduction_80c=0.0, deduction_80d=0.0, deduction_hra=0.0, hra_inputs=None):
    income = max(0.0, float(income or 0.0))
    deduction_80c = max(0.0, float(deduction_80c or 0.0))
    deduction_80d = max(0.0, float(deduction_80d or 0.0))
    deduction_hra = max(0.0, float(deduction_hra or 0.0))

    # Calculate HRA exemption if hra_inputs is provided
    hra_details = None
    if hra_inputs:
        hra_details = calculate_hra_exemption(
            basic_salary=hra_inputs.get("basic_salary", 0.0),
            rent_paid=hra_inputs.get("rent_paid", 0.0),
            hra_received=hra_inputs.get("hra_received", 0.0),
            is_metro=hra_inputs.get("is_metro", False)
        )
        deduction_hra = hra_details["calculated_exemption"]

    # 1. New Regime Calculation (FY 2026-27)
    std_deduction_new = 75000
    taxable_new = max(0.0, income - std_deduction_new)
    
    tax_new = 0.0
    # Slabs:
    # 0 - 4L: 0%
    # 4L - 8L: 5%
    # 8L - 12L: 10%
    # 12L - 16L: 15%
    # 16L - 20L: 20%
    # 20 - 24L: 25%
    # >24L : 30%
    if taxable_new <= 400000:
        tax_new = 0.0
    elif taxable_new <= 800000:
        tax_new = (taxable_new - 400000) * 0.05
    elif taxable_new <= 1200000:
        tax_new = 400000 * 0.05 + (taxable_new - 800000) * 0.10
    elif taxable_new <= 1600000:
        tax_new = 400000 * 0.05 + 400000 * 0.10 + (taxable_new - 1200000) * 0.15
    elif taxable_new <= 2000000:
        tax_new = 400000 * 0.05 + 400000 * 0.10 + 400000 * 0.15 + (taxable_new - 1600000) * 0.20
    elif taxable_new <= 2400000:
        tax_new = 400000 * 0.05 + 400000 * 0.10 + 400000 * 0.15 + 400000 * 0.20 + (taxable_new - 2000000) * 0.25
    else:
        tax_new = 400000 * 0.05 + 400000 * 0.10 + 400000 * 0.15 + 400000 * 0.20 + 400000 * 0.25 + (taxable_new - 2400000) * 0.30
        
    # Rebate under Sec 87A for New Regime:
    if taxable_new <= 1200000:
        tax_new = 0.0
    # marginal relief
    else:
        diff_amt = taxable_new - 1200000
        if diff_amt <= tax_new:
            tax_new = diff_amt

    # surcharge
    if taxable_new <= 5000000:
        surcharge_rate = 0.0
    elif taxable_new <= 10000000:
        surcharge_rate = 10.0
    elif taxable_new <= 200000000:
        surcharge_rate = 15.0
    else:
        surcharge_rate = 25.0
    surcharge = tax_new * (surcharge_rate / 100)
        
    cess_new = tax_new * 0.04
    total_new = round(tax_new + cess_new + surcharge, 2)
    
    # 2. Old Regime Calculation with custom deductions
    # Deductions cap logic:
    # 80C capped at 1.5 Lakhs (150,000)
    # 80D capped at 25,000 (standard limit)
    ded_80c = min(150000.0, deduction_80c)
    ded_80d = min(25000.0, deduction_80d)
    ded_hra = deduction_hra
    
    std_deduction_old = 50000
    total_deductions_old = std_deduction_old + ded_80c + ded_80d + ded_hra
    taxable_old = max(0.0, income - total_deductions_old)
    
    tax_old = 0.0
    # Slabs:
    # 0 - 2.5L: 0%
    # 2.5L - 5L: 5%
    # 5L - 10L: 20%
    # >10L: 30%
    if taxable_old <= 250000:
        tax_old = 0.0
    elif taxable_old <= 500000:
        tax_old = (taxable_old - 250000) * 0.05
    elif taxable_old <= 1000000:
        tax_old = 250000 * 0.05 + (taxable_old - 500000) * 0.20
    else:
        tax_old = 250000 * 0.05 + 500000 * 0.20 + (taxable_old - 1000000) * 0.30
        
    # Rebate under Sec 87A for Old Regime:
    if taxable_old <= 500000:
        tax_old = 0.0
        
    cess_old = tax_old * 0.04
    # surcharge
    if taxable_old <= 5000000:
        surcharge_rate_ = 0.0
    elif taxable_old <= 10000000:
        surcharge_rate_ = 10.0
    elif taxable_old <= 200000000:
        surcharge_rate_ = 15.0
    elif taxable_old <= 50000000:
        surcharge_rate_ = 25.0
    else:
        surcharge_rate_ = 37.0
    surcharge_old = tax_old * (surcharge_rate_ / 100)

    total_old = round(tax_old + cess_old + surcharge_old, 2)
    
    is_equal = (total_new == total_old)
    recommended_regime = "New Regime" if total_new < total_old else "Old Regime"

    res_dict = {
        "gross_income": income,
        "deductions_applied": {
            "standard_deduction": std_deduction_old,
            "80c": ded_80c,
            "80d": ded_80d,
            "hra": ded_hra,
            "total": total_deductions_old
        },
        "new_regime": {
            "standard_deduction": std_deduction_new,
            "total_deductions": std_deduction_new,
            "taxable_income": taxable_new,
            "base_tax": round(tax_new, 2),
            "cess": round(cess_new, 2),
            "surcharge": round(surcharge, 2),
            "total_tax": total_new,
        },
        "old_regime": {
            "standard_deduction": std_deduction_old,
            "total_deductions": total_deductions_old,
            "taxable_income": taxable_old,
            "base_tax": round(tax_old, 2),
            "cess": round(cess_old, 2),
            "surcharge": round(surcharge_old, 2),
            "total_tax": total_old
        },
        "is_equal": is_equal,
        "recommended": recommended_regime,
        "savings": round(abs(total_old - total_new), 2)
    }

    if hra_details:
        res_dict["hra_exemption_details"] = hra_details

    return res_dict


def _r2(x):
    return round(float(x), 2)


def _tax_total_for_regime(calc_result, regime_key):
    return float(calc_result[regime_key]["total_tax"])


def _sensitivity_by_rupee(income, deduction_80c=0.0, deduction_80d=0.0, deduction_hra=0.0):
    """
    Returns marginal tax deltas per ₹1 change in each deduction, computed via
    finite difference: tax(d+1) - tax(d). Caps in calculate_tax naturally apply.
    """
    base = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=deduction_80d, deduction_hra=deduction_hra)

    deltas = {
        "new_regime": {"80c_delta_per_1": 0.0, "80d_delta_per_1": 0.0, "hra_delta_per_1": 0.0},
        "old_regime": {"80c_delta_per_1": 0.0, "80d_delta_per_1": 0.0, "hra_delta_per_1": 0.0},
    }

    # 80C (+1)
    plus_80c = calculate_tax(income, deduction_80c=deduction_80c + 1, deduction_80d=deduction_80d, deduction_hra=deduction_hra)
    deltas["new_regime"]["80c_delta_per_1"] = _r2(_tax_total_for_regime(plus_80c, "new_regime") - _tax_total_for_regime(base, "new_regime"))
    deltas["old_regime"]["80c_delta_per_1"] = _r2(_tax_total_for_regime(plus_80c, "old_regime") - _tax_total_for_regime(base, "old_regime"))

    # 80D (+1)
    plus_80d = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=deduction_80d + 1, deduction_hra=deduction_hra)
    deltas["new_regime"]["80d_delta_per_1"] = _r2(_tax_total_for_regime(plus_80d, "new_regime") - _tax_total_for_regime(base, "new_regime"))
    deltas["old_regime"]["80d_delta_per_1"] = _r2(_tax_total_for_regime(plus_80d, "old_regime") - _tax_total_for_regime(base, "old_regime"))

    # HRA (+1)
    plus_hra = calculate_tax(income, deduction_80c=deduction_80c, deduction_80d=deduction_80d, deduction_hra=deduction_hra + 1)
    deltas["new_regime"]["hra_delta_per_1"] = _r2(_tax_total_for_regime(plus_hra, "new_regime") - _tax_total_for_regime(base, "new_regime"))
    deltas["old_regime"]["hra_delta_per_1"] = _r2(_tax_total_for_regime(plus_hra, "old_regime") - _tax_total_for_regime(base, "old_regime"))

    return deltas


def simulate_tax_scenarios(
    income,
    scenario_a,
    scenario_b,
):
    """
    scenario_a / scenario_b are dicts with:
      - deduction_80c
      - deduction_80d
      - deduction_hra

    Returns deterministic output:
      - scenario_a: full calculate_tax output
      - scenario_b: full calculate_tax output
      - scenario switch deltas (A -> B): total tax deltas per regime
      - sensitivity deltas per ₹1 change in each deduction for each scenario+regime
      - deterministic lever ranking for offline explanation
    """
    def _pick(sc):
        hra_inputs = sc.get("hra_inputs")
        if hra_inputs:
            hra_inputs = {
                "basic_salary": float(hra_inputs.get("basic_salary", 0.0)),
                "rent_paid": float(hra_inputs.get("rent_paid", 0.0)),
                "hra_received": float(hra_inputs.get("hra_received", 0.0)),
                "is_metro": bool(hra_inputs.get("is_metro", False))
            }
        return {
            "deduction_80c": float(sc.get("deduction_80c", 0.0)),
            "deduction_80d": float(sc.get("deduction_80d", 0.0)),
            "deduction_hra": float(sc.get("deduction_hra", 0.0)),
            "hra_inputs": hra_inputs,
        }

    a_in = _pick(scenario_a)
    b_in = _pick(scenario_b)

    a_calc = calculate_tax(
        income,
        deduction_80c=a_in["deduction_80c"],
        deduction_80d=a_in["deduction_80d"],
        deduction_hra=a_in["deduction_hra"],
        hra_inputs=a_in["hra_inputs"],
    )
    b_calc = calculate_tax(
        income,
        deduction_80c=b_in["deduction_80c"],
        deduction_80d=b_in["deduction_80d"],
        deduction_hra=b_in["deduction_hra"],
        hra_inputs=b_in["hra_inputs"],
    )

    # Switching A -> B deltas (B - A)
    delta_new_total = _r2(b_calc["new_regime"]["total_tax"] - a_calc["new_regime"]["total_tax"])
    delta_old_total = _r2(b_calc["old_regime"]["total_tax"] - a_calc["old_regime"]["total_tax"])

    # "Savings under new regime" when switching A -> B
    # If delta is negative, B saves; we report positive savings amount.
    new_savings_switch = _r2(max(0.0, -delta_new_total))
    old_savings_switch = _r2(max(0.0, -delta_old_total))

    # Sensitivity (per ₹1 change) for each scenario
    a_sens = _sensitivity_by_rupee(
        income,
        deduction_80c=a_in["deduction_80c"],
        deduction_80d=a_in["deduction_80d"],
        deduction_hra=a_in["deduction_hra"],
    )
    b_sens = _sensitivity_by_rupee(
        income,
        deduction_80c=b_in["deduction_80c"],
        deduction_80d=b_in["deduction_80d"],
        deduction_hra=b_in["deduction_hra"],
    )

    def _rank_levers(sens_for_regime):
        # Most negative delta per ₹1 reduces tax (best). If all >=0, still return largest deltas first.
        candidates = [
            ("80C", sens_for_regime["80c_delta_per_1"]),
            ("80D", sens_for_regime["80d_delta_per_1"]),
            ("HRA", sens_for_regime["hra_delta_per_1"]),
        ]
        candidates_sorted = sorted(candidates, key=lambda x: x[1])  # ascending (more negative first)
        return [
            {
                "lever": name,
                "delta_per_1": float(delta),
            }
            for name, delta in candidates_sorted
        ]

    best_regime_a = a_calc["recommended"]
    best_regime_b = b_calc["recommended"]

    # For deterministic offline explanation, choose lever ranking for each scenario's recommended regime.
    sens_a_for_best = a_sens["new_regime"] if best_regime_a == "New Regime" else a_sens["old_regime"]
    sens_b_for_best = b_sens["new_regime"] if best_regime_b == "New Regime" else b_sens["old_regime"]

    comparison = {
        "switch": {
            "new_regime": {"delta_total_tax": delta_new_total, "savings": new_savings_switch},
            "old_regime": {"delta_total_tax": delta_old_total, "savings": old_savings_switch},
        },
        "best_scenario_by_savings_under_recommended_regime": (
            "A" if (a_calc["savings"] >= b_calc["savings"]) else "B"
        ),
        "best_regime": {
            "scenario_a": best_regime_a,
            "scenario_b": best_regime_b,
        },
    }

    return {
        "income": float(income),
        "scenario_a": a_calc,
        "scenario_b": b_calc,
        "comparison": comparison,
        "sensitivity": {
            "scenario_a": {
                "new_regime": a_sens["new_regime"],
                "old_regime": a_sens["old_regime"],
                "lever_ranking_for_best_regime": _rank_levers(sens_a_for_best),
            },
            "scenario_b": {
                "new_regime": b_sens["new_regime"],
                "old_regime": b_sens["old_regime"],
                "lever_ranking_for_best_regime": _rank_levers(sens_b_for_best),
            },
        },
    }


from typing import Dict, Any

from typing import Dict, Any


def tax_optimization_module(income: float, expenses: Dict[str, float], investments: Dict[str, float]) -> Dict[str, Any]:
    """
    Note: this module applies 80C/80D/HRA-style deductions in a single
    Old-Regime-style calculation. It does NOT compare against New Regime tax
    (which is flat regardless of these deductions, per calculate_tax()).
    """

    SLABS = [
        (0, 300000, 0.00),
        (300000, 700000, 0.05),
        (700000, 1000000, 0.10),
        (1000000, 1200000, 0.15),
        (1200000, 1500000, 0.20),
        (1500000, float('inf'), 0.30),
    ]

    CESS_RATE = 0.04
    REBATE_THRESHOLD = 700000
    STANDARD_DEDUCTION = 75000

    DEDUCTION_RULES = {
        "80C": {"cap": 150000, "description": "investments in PPF, ELSS, life insurance, etc."},
        "80D": {"cap": 25000, "description": "medical insurance premium"},
        "HRA": {"cap": None, "description": "House Rent Allowance exemption"},
    }

    deductible_expenses = sum(expenses.values()) if expenses else 0.0
    gross_taxable_income = max(0.0, income - deductible_expenses)

    current_deductions = STANDARD_DEDUCTION
    for section, rule in DEDUCTION_RULES.items():
        invested = investments.get(section, 0)
        cap = rule["cap"]
        current_deductions += min(invested, cap) if cap is not None else invested

    current_taxable_income = max(0.0, gross_taxable_income - current_deductions)

    tax = 0.0
    for lower, upper, rate in SLABS:
        if current_taxable_income > lower:
            tax += (min(current_taxable_income, upper) - lower) * rate
        else:
            break

    current_tax = 0.0 if current_taxable_income <= REBATE_THRESHOLD else round(tax * (1 + CESS_RATE), 2)

    marginal_rate = 0.0
    for lower, upper, rate in SLABS:
        if lower < current_taxable_income <= upper:
            marginal_rate = rate

    max_deductions = STANDARD_DEDUCTION
    for section, rule in DEDUCTION_RULES.items():
        cap = rule["cap"]
        max_deductions += cap if cap is not None else investments.get(section, 0)

    optimized_taxable_income = max(0.0, gross_taxable_income - max_deductions)

    tax_opt = 0.0
    for lower, upper, rate in SLABS:
        if optimized_taxable_income > lower:
            tax_opt += (min(optimized_taxable_income, upper) - lower) * rate
        else:
            break

    optimized_tax = 0.0 if optimized_taxable_income <= REBATE_THRESHOLD else round(tax_opt * (1 + CESS_RATE), 2)

    potential_savings = round(current_tax - optimized_tax, 2)

    suggestions = {}
    for section, rule in DEDUCTION_RULES.items():
        cap = rule["cap"]
        if cap is None:
            continue
        invested = investments.get(section, 0)
        gap = cap - invested
        if gap > 0:
            estimated_savings = round(gap * marginal_rate, 2)
            if estimated_savings > 0:
                suggestions[section] = (
                    f"Invest Rs. {gap:,.0f} more under {section} "
                    f"({rule['description']}) to save up to Rs. {estimated_savings:,.0f} tax."
                )

    if not suggestions:
        suggestions["info"] = "Your current deductions are already well optimized for this income level."

    regime_note = None
    if potential_savings > 0:
        regime_note = (
            "These savings assume filing under the Old Tax Regime, since 80C/80D/HRA "
            "deductions don't apply under the New Regime."
        )

    return {
        "current_tax": current_tax,
        "optimized_tax": optimized_tax,
        "potential_savings": potential_savings,
        "suggestions": suggestions,
        "regime_note": regime_note,
    }
