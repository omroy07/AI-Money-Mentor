"""Deterministic financial goal planning engine.

All calculations use Decimal for precision and are purely mathematical —
no AI, no network calls, no randomness.  The AI layer (goal_explainer.py)
consumes the structured output and provides explanations/personalisation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants / thresholds for feasibility assessment
# ---------------------------------------------------------------------------
SAVINGS_RATIO_COMFORTABLE: Decimal = Decimal("0.20")   # ≤20% of income
SAVINGS_RATIO_STRETCH: Decimal = Decimal("0.40")       # 20–40% of income
# Kept for backward compatibility; the >40% band is now "stretch (aggressive)"
# when the surplus covers it (see assess_feasibility), so this alias equals
# SAVINGS_RATIO_STRETCH and is no longer a hard gate on its own.
SAVINGS_RATIO_NOT_FEASIBLE: Decimal = Decimal("0.40")  # >40% of income


@dataclass
class GoalPlannerResult:
    """Structured result from the deterministic goal planner."""

    required_monthly_savings: Decimal
    status: str  # "feasible", "stretch", "not_feasible"
    savings_ratio: Decimal  # required / income
    months: int
    message: str
    # Additional info for the AI layer
    target: Decimal = Decimal("0")
    available_surplus: Optional[Decimal] = None
    current_savings: Decimal = Decimal("0")
    income: Optional[Decimal] = None
    expenses: Optional[Decimal] = None
    # Hard achievability gate (surplus covers required); ratio only grades
    # comfort via `status`. Added with a default so existing constructions
    # keep working and existing keys in to_dict() are unchanged.
    achievable: bool = True

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict (floats) for the API / AI layer."""
        return {
            "target": float(self.target),
            "required_monthly_savings": float(self.required_monthly_savings),
            "status": self.status,
            "achievable": self.achievable,
            "savings_ratio": float(self.savings_ratio),
            "savings_ratio_pct": round(float(self.savings_ratio * 100), 1),
            "months": self.months,
            "message": self.message,
            "available_surplus": float(self.available_surplus) if self.available_surplus is not None else None,
            "current_savings": float(self.current_savings),
            "income": float(self.income) if self.income is not None else None,
            "expenses": float(self.expenses) if self.expenses is not None else None,
        }


def _to_decimal(value: Optional[float | int | str | Decimal]) -> Decimal:
    """Coerce a value to Decimal; return Decimal('0') if None."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _validate_positive(name: str, value: Decimal, *, allow_zero: bool = False) -> None:
    """Raise ValueError if value is invalid."""
    d = _to_decimal(value)
    if allow_zero:
        if d < Decimal(0):
            raise ValueError(f"{name} cannot be negative")
        return
    if d <= Decimal(0):
        raise ValueError(f"{name} must be positive")


def required_monthly_savings(
    target: float | int | str | Decimal,
    months: int,
    current_savings: float | int | str | Decimal = 0,
    expected_return: float | int | str | Decimal = 0,
) -> Decimal:
    """Calculate the required monthly savings to reach a target.

    Parameters
    ----------
    target : total amount needed (in rupees)
    months : number of months to reach the goal
    current_savings : already saved amount (default 0)
    expected_return : annual expected return rate (%); not used in the
        basic deterministic version — kept for API compatibility.

    Returns
    -------
    Monthly savings amount (Decimal)
    """
    _validate_positive("target", target, allow_zero=False)
    _validate_positive("months", months, allow_zero=False)
    _validate_positive("current_savings", current_savings, allow_zero=True)

    months_d = _to_decimal(months)
    target_d = _to_decimal(target)
    current_d = _to_decimal(current_savings)

    if current_d >= target_d:
        return Decimal("0")

    remaining = target_d - current_d
    monthly = (remaining / months_d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return monthly


def assess_feasibility(
    required: float | int | str | Decimal,
    income: float | int | str | Decimal,
    expenses: Optional[float | int | str | Decimal] = None,
) -> GoalPlannerResult:
    """Assess whether a monthly savings requirement is feasible.

    The available monthly surplus (income − expenses) is the hard
    achievability gate, exposed as ``achievable``:

    - required > surplus → not achievable → "not_feasible"
    - required <= surplus → achievable → comfort comes from the ratio

    The savings‑ratio (required / income) only grades comfort:

    - ≤ 20%     → "feasible" (comfortable)
    - 20–40%    → "stretch"
    - > 40%     → "stretch" flagged as aggressive (leaves little or no
      buffer), provided the surplus covers it; "not_feasible" only when
      the surplus is insufficient or unknown.

    If *expenses* are omitted, the surplus is unknown and the ratio rule
    alone decides (as before): > 40% → "not_feasible".

    Parameters
    ----------
    required : required monthly savings (Decimal/int/float/str)
    income : monthly income (Decimal/int/float/str)
    expenses : optional monthly expenses; if omitted, only the ratio rule
        is applied.

    Returns
    -------
    GoalPlannerResult with status, achievable, savings_ratio, and a message.
    """
    _validate_positive("income", income, allow_zero=False)

    req_d = _to_decimal(required)
    inc_d = _to_decimal(income)
    exp_d = _to_decimal(expenses) if expenses is not None else None

    # --- Savings-ratio rule ---
    if inc_d == Decimal(0):
        raise ValueError(" income must be positive")

    savings_ratio = (req_d / inc_d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if savings_ratio <= SAVINGS_RATIO_COMFORTABLE:
        comfort_status = "feasible"
    else:
        comfort_status = "stretch"
    aggressive = savings_ratio > SAVINGS_RATIO_STRETCH

    # --- Surplus (hard achievability gate) ---
    # If expenses are given and required exceeds the monthly surplus
    # (income - expenses), the goal is not achievable regardless of ratio.
    # Otherwise the goal is achievable and the ratio only grades comfort;
    # a covered surplus never downgrades a "stretch" to "feasible".
    if exp_d is not None:
        if exp_d < Decimal(0):
            raise ValueError("expenses cannot be negative")
        surplus = inc_d - exp_d
        if req_d > surplus:
            final_status = "not_feasible"
            achievable = False
        else:
            final_status = comfort_status
            achievable = True
    else:
        # No expenses provided – surplus unknown, ratio rule alone decides
        # (preserved behaviour): > 40% → "not_feasible".
        if aggressive:
            final_status = "not_feasible"
        else:
            final_status = comfort_status
        achievable = final_status != "not_feasible"

    # Build a user-facing message
    ratio_pct = (savings_ratio * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if exp_d is not None:
        surplus_d = inc_d - exp_d
        surplus_pct = (surplus_d / inc_d * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        message = (
            f"Required savings of ₹{req_d:,.2f} represent {ratio_pct}% of your "
            f"₹{inc_d:,.2f} monthly income. "
            f"After expenses (₹{exp_d:,.2f}), your monthly surplus is "
            f"₹{surplus_d:,.2f} ({surplus_pct}%). "
            f"This is '{final_status}'."
        )
    else:
        message = (
            f"Required savings of ₹{req_d:,.2f} represent {ratio_pct}% of your "
            f"₹{inc_d:,.2f} monthly income. "
            f"This is '{final_status}'."
        )
    if achievable and aggressive and exp_d is not None:
        message += (
            " Note: this is aggressive — saving over 40% of income leaves "
            "little or no buffer for unexpected costs."
        )

    return GoalPlannerResult(
        required_monthly_savings=req_d,
        status=final_status,
        savings_ratio=savings_ratio,
        months=0,  # will be filled in by caller if needed
        message=message,
        target=req_d,  # placeholder; plan_goal() overwrites with real target
        available_surplus=inc_d - exp_d if exp_d is not None else None,
        current_savings=Decimal("0"),
        income=inc_d,
        expenses=exp_d,
        achievable=achievable,
    )


def estimate_time_to_goal(
    target: float | int | str | Decimal,
    monthly_savings: float | int | str | Decimal,
) -> int:
    """Estimate how many months it will take to reach a target.

    Returns the ceiling of (target / monthly_savings).
    """
    _validate_positive("target", target, allow_zero=False)
    _validate_positive("monthly_savings", monthly_savings, allow_zero=False)

    target_d = _to_decimal(target)
    monthly_d = _to_decimal(monthly_savings)

    if monthly_d <= Decimal(0):
        raise ValueError("monthly_savings must be positive")

    months_float = target_d / monthly_d
    # ceiling without math module
    months_int = int(months_float)
    if months_int < months_float:
        months_int += 1
    return months_int


def suggest_budget_adjustments(
    expenses_by_category: Dict[str, float | int | str | Decimal],
    gap: float | int | str | Decimal,
) -> Dict[str, Decimal]:
    """Suggest which discretionary categories to trim to close a savings gap.

    The function trims categories in order of typical discretionary spend:
    dining_out, entertainment, hobbies, miscellaneous.

    Returns a dict of {category: new_amount} for adjusted categories.
    """
    _validate_positive("gap", gap, allow_zero=True)

    gap_d = _to_decimal(gap)

    # Typical discretionary order (can be customised)
    discretionary_order: List[str] = [
        "dining_out",
        "entertainment",
        "hobbies",
        "miscellaneous",
        "subscriptions",
    ]

    adjusted: Dict[str, Decimal] = {}
    remaining_gap = gap_d

    for cat in discretionary_order:
        if cat not in expenses_by_category:
            continue
        current = _to_decimal(expenses_by_category[cat])
        if current <= remaining_gap:
            # Trim the whole category
            adjusted[cat] = Decimal("0")
            remaining_gap -= current
        else:
            # Partial trim
            adjusted[cat] = current - remaining_gap
            remaining_gap = Decimal("0")
            break

    # If we still have a gap after trimming known discretionary categories,
    # return what we have and let the AI layer suggest further options.
    return adjusted


def generate_alternatives(
    target: float | int | str | Decimal,
    months: int,
    income: float | int | str | Decimal,
    current_savings: float | int | str | Decimal = 0,
    *,
    extended_months: Optional[int] = None,
    reduced_target: Optional[float | int | str | Decimal] = None,
    partial_down_payment: Optional[float | int | str | Decimal] = None,
    cheaper_option_target: Optional[float | int | str | Decimal] = None,
) -> List[GoalPlannerResult]:
    """Generate alternative scenarios for a financial goal.

    Returns a list of GoalPlannerResult objects for each alternative:
    1. Extended timeline (same target, more months)
    2. Reduced target (same months, less target)
    3. Partial down payment (save part now, finance rest later)
    4. Cheaper option (lower target for a "used" or budget version)

    Only parameters explicitly provided are included in the output.
    """
    _validate_positive("target", target, allow_zero=False)
    _validate_positive("months", months, allow_zero=False)
    _validate_positive("income", income, allow_zero=False)
    _validate_positive("current_savings", current_savings, allow_zero=True)

    results: List[GoalPlannerResult] = []

    # 1. Extended timeline
    if extended_months is not None and extended_months > months:
        monthly = required_monthly_savings(
            target=target, months=extended_months, current_savings=current_savings
        )
        assess = assess_feasibility(monthly, income)
        assess_months = estimate_time_to_goal(target, monthly)
        results.append(
            GoalPlannerResult(
                required_monthly_savings=monthly,
                status=assess.status,
                savings_ratio=assess.savings_ratio,
                months=assess_months,
                message=assess.message,
                target=_to_decimal(target),
                available_surplus=assess.available_surplus,
                current_savings=_to_decimal(current_savings),
                income=_to_decimal(income),
                expenses=assess.expenses,
            )
        )

    # 2. Reduced target
    if reduced_target is not None:
        if _to_decimal(reduced_target) <= Decimal(0):
            raise ValueError("reduced_target must be positive")
        monthly = required_monthly_savings(
            target=reduced_target, months=months, current_savings=current_savings
        )
        assess = assess_feasibility(monthly, income)
        assess_months = estimate_time_to_goal(reduced_target, monthly)
        results.append(
            GoalPlannerResult(
                required_monthly_savings=monthly,
                status=assess.status,
                savings_ratio=assess.savings_ratio,
                months=assess_months,
                message=assess.message,
                target=_to_decimal(reduced_target),
                available_surplus=assess.available_surplus,
                current_savings=_to_decimal(current_savings),
                income=_to_decimal(income),
                expenses=assess.expenses,
            )
        )

    # 3. Partial down payment
    if partial_down_payment is not None:
        down_payment_d = _to_decimal(partial_down_payment)
        if down_payment_d <= Decimal(0) or down_payment_d >= _to_decimal(target):
            raise ValueError("partial_down_payment must be positive and less than target")
        remaining_target = _to_decimal(target) - down_payment_d
        monthly = required_monthly_savings(
            target=remaining_target, months=months, current_savings=Decimal("0")
        )
        assess = assess_feasibility(monthly, income)
        assess_months = estimate_time_to_goal(remaining_target, monthly)
        results.append(
            GoalPlannerResult(
                required_monthly_savings=monthly,
                status=assess.status,
                savings_ratio=assess.savings_ratio,
                months=assess_months,
                message=assess.message,
                target=remaining_target,
                available_surplus=assess.available_surplus,
                current_savings=down_payment_d,
                income=_to_decimal(income),
                expenses=assess.expenses,
            )
        )

    # 4. Cheaper option
    if cheaper_option_target is not None:
        cheaper_d = _to_decimal(cheaper_option_target)
        if cheaper_d <= Decimal(0):
            raise ValueError("cheaper_option_target must be positive")
        monthly = required_monthly_savings(
            target=cheaper_d, months=months, current_savings=current_savings
        )
        assess = assess_feasibility(monthly, income)
        assess_months = estimate_time_to_goal(cheaper_d, monthly)
        results.append(
            GoalPlannerResult(
                required_monthly_savings=monthly,
                status=assess.status,
                savings_ratio=assess.savings_ratio,
                months=assess_months,
                message=assess.message,
                target=cheaper_d,
                available_surplus=assess.available_surplus,
                current_savings=_to_decimal(current_savings),
                income=_to_decimal(income),
                expenses=assess.expenses,
            )
        )

    return results


def plan_goal(
    target: float | int | str | Decimal,
    months: int,
    income: float | int | str | Decimal,
    expenses: Optional[float | int | str | Decimal] = None,
    current_savings: float | int | str | Decimal = 0,
    expected_return: float | int | str | Decimal = 0,
    expenses_by_category: Optional[Dict[str, float | int | str | Decimal]] = None,
) -> dict:
    """Run the full deterministic pipeline and return a JSON-ready dict.

    This keeps the Flask route thin: all maths lives here. The dict it
    returns is passed unchanged to the AI explainer layer.
    """
    target_d = _to_decimal(target)
    income_d = _to_decimal(income)
    current_d = _to_decimal(current_savings)
    expenses_d = _to_decimal(expenses) if expenses is not None else None

    required = required_monthly_savings(
        target=target_d,
        months=months,
        current_savings=current_d,
        expected_return=expected_return,
    )

    if required == Decimal("0"):
        months_needed = 0
    else:
        months_needed = estimate_time_to_goal(target_d, required)

    assessment = assess_feasibility(required, income_d, expenses_d)
    assessment.target = target_d
    assessment.months = int(months)
    assessment.current_savings = current_d

    # Budget gap: how much the required amount exceeds the cash surplus.
    budget_adjustments: Dict[str, Decimal] = {}
    gap = Decimal("0")
    if expenses_d is not None:
        surplus = income_d - expenses_d
        if required > surplus:
            gap = (required - surplus).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            budget_adjustments = suggest_budget_adjustments(
                expenses_by_category or {}, gap
            )

    alternatives = generate_alternatives(
        target=target_d,
        months=int(months),
        income=income_d,
        current_savings=current_d,
        extended_months=int(months) * 2,
        reduced_target=(target_d * Decimal("0.7")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        cheaper_option_target=(target_d * Decimal("0.6")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
    )

    return {
        "target": float(target_d),
        "months": int(months),
        "income": float(income_d),
        "expenses": float(expenses_d) if expenses_d is not None else None,
        "current_savings": float(current_d),
        "required_monthly_savings": float(required),
        "status": assessment.status,
        "achievable": assessment.achievable,
        "savings_ratio": float(assessment.savings_ratio),
        "savings_ratio_pct": round(float(assessment.savings_ratio * 100), 1),
        "months_to_goal": months_needed,
        "message": assessment.message,
        "available_surplus": float(assessment.available_surplus)
        if assessment.available_surplus is not None
        else None,
        "gap": float(gap),
        "budget_adjustments": {k: float(v) for k, v in budget_adjustments.items()},
        "alternatives": [
            {**alt.to_dict(), "kind": kind}
            for alt, kind in zip(
                alternatives,
                ["extended_timeline", "reduced_target", "cheaper_option"],
            )
        ],
        "assessment": assessment,
    }