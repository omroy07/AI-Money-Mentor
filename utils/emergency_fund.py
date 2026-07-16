def calculate_emergency_fund(
    monthly_expenses,
    dependents=0,
    dual_income=False,
    current_savings=0,
    crisis_type="normal"
):
    """
    Calculate recommended emergency fund and crisis runway.
    """

    # Base recommendation: 6 months
    recommended_months = 6

    # Add one month per dependent
    recommended_months += dependents

    # Single-income households need extra protection
    if not dual_income:
        recommended_months += 2

    # Crisis scenarios
    crisis_multiplier = {
        "normal": 1.0,
        "job_loss": 1.0,
        "medical": 1.5,
        "recession": 1.25
    }

    multiplier = crisis_multiplier.get(crisis_type, 1.0)

    adjusted_monthly_expense = monthly_expenses * multiplier

    if adjusted_monthly_expense == 0:
        runway_months = 0
    else:
        runway_months = round(
            current_savings / adjusted_monthly_expense,
            2
        )

    return {
        "recommended_fund": round(
            monthly_expenses * recommended_months,
            2
        ),
        "recommended_months": recommended_months,
        "runway_months": runway_months,
        "monthly_expenses": monthly_expenses,
        "current_savings": current_savings,
        "dependents": dependents,
        "dual_income": dual_income,
        "crisis_type": crisis_type
    }