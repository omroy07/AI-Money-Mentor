"""
Portfolio explanation module.
Provides deterministic templates and AI-powered explanations for portfolio risk analysis.
"""
import os
import json
from typing import Dict, Any, Tuple

from utils.portfolio_risk import analyze_portfolio
from utils.config import GROQ_MODEL


def build_ai_payload(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only computed figures for the AI, removing user-controlled names."""
    weights = analysis.get("weights", {})
    asset_class_weights = weights.get("asset_classes", {})

    flags = analysis.get("concentration_flags", [])
    flag_messages = [f.get("message") for f in flags]

    scenarios = analysis.get("scenarios", [])
    scenario_data = {
        s.get("name"): s.get("portfolio_change_percent")
        for s in scenarios
    }

    return {
        "total_value": analysis.get("total_value"),
        "expected_return_percent": analysis.get("expected_return_percent"),
        "volatility_percent": analysis.get("volatility_percent"),
        "sharpe_ratio": analysis.get("sharpe_ratio"),
        "average_correlation": analysis.get("average_correlation"),
        "risk_score": analysis.get("risk_score"),
        "risk_label": analysis.get("risk_label"),
        "diversification_score": analysis.get("diversification_score"),
        "asset_class_weights_percent": asset_class_weights,
        "concentration_flag_messages": flag_messages,
        "scenarios_change_percent": scenario_data
    }


def template_explanation(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a deterministic explanation based on risk label and flags."""
    label = analysis.get("risk_label", "Moderate")
    flags = analysis.get("concentration_flags", [])
    scenarios = analysis.get("scenarios", [])

    worst_scenario = min(scenarios, key=lambda x: x.get("portfolio_change_percent", 0), default={})
    worst_name = worst_scenario.get("name", "downturn")
    worst_drop = worst_scenario.get("portfolio_change_percent", 0)

    summary = f"Your portfolio indicates a {label} risk profile. "
    if flags:
        summary += f"We identified {len(flags)} concentration risk(s). "
    else:
        summary += "Your assets are well distributed. "

    summary += f"In a simulated {worst_name}, your portfolio value changed by {worst_drop}%."

    tips = [
        "Regularly review your asset allocation.",
        "Ensure you have an adequate emergency fund."
    ]
    if flags:
        tips.append("Consider diversifying your concentrated positions.")

    alternatives = [
        "Increase debt share to lower volatility.",
        "Add gold or real estate for inflation protection."
    ]

    return {
        "summary": summary,
        "tips": tips[:5],
        "alternatives": alternatives[:5],
        "source": "template"
    }


def ai_explanation(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch an AI-powered explanation using Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY":
        return None

    from groq import Groq, GroqError
    try:
        client = Groq(api_key=api_key)
        payload = build_ai_payload(analysis)
        payload_str = json.dumps(payload)

        sys_msg = (
            "You are a portfolio analyst. Explain only. Use only the numbers provided. "
            "Never calculate or invent numbers. Never name specific securities or funds. "
            "No financial advice. Reply ONLY with valid JSON containing keys: "
            "summary (string, max 1200 chars), tips (list of strings, max 5), "
            "alternatives (list of asset class level ideas, max 5)."
        )

        res = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": payload_str}
            ],
            temperature=0.2,
            max_tokens=600,
            timeout=15.0
        )

        reply = res.choices[0].message.content
        if not reply:
            return None

        data = json.loads(reply)

        summary = data.get("summary")
        tips = data.get("tips")
        alts = data.get("alternatives")

        if not isinstance(summary, str) or not summary.strip() or len(summary) > 1200:
            return None
        if not isinstance(tips, list) or len(tips) > 5:
            return None
        if not isinstance(alts, list) or len(alts) > 5:
            return None

        return {
            "summary": summary,
            "tips": tips,
            "alternatives": alts,
            "source": "ai"
        }
    except (GroqError, Exception):
        return None


def build_explanation(analysis: Dict[str, Any], use_ai: bool = True) -> Dict[str, Any]:
    """Build the explanation dictionary, falling back to template if AI fails."""
    expl = None
    if use_ai:
        expl = ai_explanation(analysis)

    if expl is None:
        expl = template_explanation(analysis)

    expl["disclaimer"] = analysis.get("disclaimer", "")
    return expl


def handle_risk_request(data: Dict[str, Any], use_ai: bool = None) -> Tuple[Dict[str, Any], int]:
    """Process a portfolio risk analysis request and return payload and status."""
    if not isinstance(data, dict) or "holdings" not in data:
        return ({"error": "Missing holdings in request."}, 400)

    ai_flag = use_ai if use_ai is not None else data.get("use_ai", True)
    if not isinstance(ai_flag, bool):
        return ({"error": "use_ai must be a boolean."}, 400)

    try:
        analysis = analyze_portfolio(data["holdings"])
        if isinstance(analysis, dict) and "error" in analysis:
            return (analysis, 400)

        explanation = build_explanation(analysis, use_ai=ai_flag)
        return ({"analysis": analysis, "explanation": explanation}, 200)
    except Exception:
        return ({"error": "Portfolio analysis failed."}, 500)
