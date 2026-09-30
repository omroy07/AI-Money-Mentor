"""AI explanation layer for financial goal planning.

This module consumes the deterministic output from ``utils.goal_planner``
and passes it to Groq for:

- Explaining the calculations and results.
- Personalising recommendations.
- Communicating alternative strategies in a user-friendly way.

The prompt explicitly instructs the LLM to use only the supplied numbers
and never recalculate. A deterministic fallback template is provided so
the endpoint still returns a sensible message if Groq fails or times out.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Union

from groq import Groq, GroqError

from utils.config import GROQ_MODEL
from utils.goal_planner import GoalPlannerResult

ResultLike = Union[GoalPlannerResult, Dict[str, Any]]

# ---------------------------------------------------------------------------
# Fallback template - used when Groq is unavailable, times out, or returns
# an empty response. It uses only numbers already computed by the
# deterministic engine, so no recalculation can occur.
# ---------------------------------------------------------------------------
FALLBACK_TEMPLATE = """Here is the assessment of your financial goal:

Goal details:
- Target amount: Rs.{target:,.2f}
- Timeline: {months} months
- Monthly income: Rs.{income:,.2f}
- Current savings: Rs.{current_savings:,.2f}
- Required monthly savings: Rs.{required:,.2f}

Feasibility assessment:
- Status: {status}
- Savings ratio: {ratio_pct:.1f}% of your income
{surplus_info}
{message}

How to interpret the status:
- feasible: the required savings are up to 20% of income. You can reach this goal comfortably.
- stretch: the required savings are over 20% of income but your surplus covers them. Achievable if you trim discretionary spending or add income. Over 40% is aggressive and leaves little or no buffer.
- not_feasible: the required savings exceed your monthly surplus (or exceed 40% of income when your surplus is unknown). Consider an extended timeline, reduced target, partial down payment, or cheaper option.

Suggested next steps:
1. Review monthly expenses and trim discretionary categories first.
2. Consider extending the timeline to lower the monthly requirement.
3. Check whether a reduced target or partial down payment still meets your needs.
4. Look for ways to increase income toward the goal.

All numbers above come from the values you provided; nothing was recalculated here."""


def _as_numbers(result: ResultLike) -> Dict[str, Any]:
    """Normalise a GoalPlannerResult or plan_goal() dict to plain numbers."""
    if isinstance(result, dict):
        assessment = result.get("assessment")
        if isinstance(assessment, GoalPlannerResult):
            base = assessment.to_dict()
            # Prefer top-level computed values from plan_goal() when present.
            for key in (
                "target",
                "months",
                "income",
                "expenses",
                "current_savings",
                "required_monthly_savings",
                "status",
                "savings_ratio_pct",
                "months_to_goal",
                "message",
                "available_surplus",
            ):
                if key in result and result[key] is not None:
                    base[key] = result[key]
            numbers = base
        else:
            numbers = dict(result)
        numbers.setdefault("target", numbers.get("required_monthly_savings", 0))
        numbers.setdefault("months", numbers.get("months_to_goal", 0))
        numbers.setdefault("income", 0)
        numbers.setdefault("current_savings", 0)
        numbers.setdefault("required_monthly_savings", 0)
        numbers.setdefault("status", "not_feasible")
        if "savings_ratio_pct" not in numbers:
            ratio = float(numbers.get("savings_ratio", 0) or 0)
            numbers["savings_ratio_pct"] = round(ratio * 100, 1)
        numbers.setdefault("message", "")
        numbers.setdefault("available_surplus", None)
        return numbers
    return result.to_dict()


def _format_surplus_info(numbers: Dict[str, Any]) -> str:
    """Format the surplus line for the fallback template."""
    surplus = numbers.get("available_surplus")
    income = numbers.get("income") or 0
    if surplus is None or not income:
        return ""
    try:
        pct = (
            Decimal(str(surplus)) / Decimal(str(income)) * Decimal("100")
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    except Exception:
        return ""
    return f"- Monthly surplus (income minus expenses): Rs.{float(surplus):,.2f} ({pct}% of income)"


def render_fallback(result: ResultLike) -> str:
    """Render the deterministic fallback message. Never calls the network."""
    numbers = _as_numbers(result)
    return FALLBACK_TEMPLATE.format(
        target=float(numbers.get("target") or 0),
        months=int(numbers.get("months") or 0),
        income=float(numbers.get("income") or 0),
        current_savings=float(numbers.get("current_savings") or 0),
        required=float(numbers.get("required_monthly_savings") or 0),
        status=numbers.get("status", "not_feasible"),
        ratio_pct=float(numbers.get("savings_ratio_pct") or 0),
        surplus_info=_format_surplus_info(numbers),
        message=numbers.get("message") or "",
    )


def build_goal_prompt(result: ResultLike) -> str:
    """Build the Groq prompt. States the use-only-supplied-numbers rule."""
    numbers = _as_numbers(result)
    surplus = numbers.get("available_surplus")
    surplus_line = (
        f"- Monthly surplus: Rs.{float(surplus):,.2f}"
        if surplus is not None
        else "- Monthly surplus: not provided"
    )
    return f"""You are AI Money Mentor, a personal finance assistant. Explain the financial goal assessment below, personalise the recommendations, and present alternative strategies.

CRITICAL INSTRUCTION: Use only the numbers below. Do NOT recalculate anything. Do not invent new numbers, percentages, or targets. All calculations have already been done by the deterministic engine. Your response must reference exactly the supplied values and explain what they mean.

Goal assessment data:
- Target amount: Rs.{float(numbers.get("target") or 0):,.2f}
- Timeline: {int(numbers.get("months") or 0)} months
- Monthly income: Rs.{float(numbers.get("income") or 0):,.2f}
- Current savings: Rs.{float(numbers.get("current_savings") or 0):,.2f}
- Required monthly savings: Rs.{float(numbers.get("required_monthly_savings") or 0):,.2f}
- Savings ratio: {float(numbers.get("savings_ratio_pct") or 0):.1f}% of income
- Feasibility status: {numbers.get("status")}
{surplus_line}
- Planner message: "{numbers.get("message") or ""}"

Please provide:
1. A clear, empathetic explanation of what the numbers mean.
2. Personalised advice for the feasibility status (feasible / stretch / not_feasible).
3. Alternative strategies if the goal is not feasible (extended timeline, reduced target, partial down payment, or cheaper option - use only the numbers above, do not invent new targets).
4. A brief actionable summary readable in under 30 seconds.

Format your response in plain text (no markdown, no code blocks). Start with a one-sentence summary, then explanation, alternatives, and action items separated by blank lines."""


def explain_goal(result: ResultLike, client: Optional[Groq] = None) -> str:
    """Generate a user-friendly AI explanation for a goal assessment.

    Parameters
    ----------
    result : GoalPlannerResult or plan_goal() dict from the deterministic planner.
    client : optional Groq client. If None, the fallback is returned immediately.

    Returns
    -------
    A string containing the AI-generated explanation (or the deterministic fallback).
    """
    if client is None:
        return render_fallback(result)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": build_goal_prompt(result)}],
            temperature=0.3,
            max_tokens=500,
        )
        ai_text = (response.choices[0].message.content or "").strip()
        if not ai_text:
            return render_fallback(result)
        return ai_text
    except (GroqError, Exception):
        # Groq API error, timeout, or network failure - deterministic fallback.
        return render_fallback(result)
