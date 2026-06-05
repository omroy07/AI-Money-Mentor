def calculate_money_score(income, expenses, savings, investments, debt, emergency_fund):
    details = calculate_money_score_details(income, expenses, savings, investments, debt, emergency_fund)
    return details["score"]

def calculate_money_score_details(income, expenses, savings, investments, debt, emergency_fund):
    score = 0

    # 1. Savings Rate (30)
    savings_rate = savings / income if income > 0 else 0.0
    savings_score = 0
    if savings_rate >= 0.3:
        savings_score = 30
    elif savings_rate >= 0.2:
        savings_score = 20
    else:
        savings_score = 10
    score += savings_score

    # 2. Investment Rate (25)
    invest_rate = investments / income if income > 0 else 0.0
    invest_score = 0
    if invest_rate >= 0.2:
        invest_score = 25
    elif invest_rate >= 0.1:
        invest_score = 15
    else:
        invest_score = 5
    score += invest_score

    # 3. Debt Ratio (25)
    debt_ratio = debt / income if income > 0 else (1.0 if debt > 0 else 0.0)
    debt_score = 0
    if debt_ratio <= 0.2:
        debt_score = 25
    elif debt_ratio <= 0.4:
        debt_score = 15
    else:
        debt_score = 5
    score += debt_score

    # 4. Emergency Fund (20)
    months_cover = emergency_fund / expenses if expenses > 0 else (12.0 if emergency_fund > 0 else 0.0)
    emergency_score = 0
    if months_cover >= 6:
        emergency_score = 20
    elif months_cover >= 3:
        emergency_score = 10
    else:
        emergency_score = 5
    score += emergency_score

    return {
        "score": round(score),
        "savings_rate": round(savings_rate * 100, 1),
        "savings_score": savings_score,
        "investment_rate": round(invest_rate * 100, 1),
        "investment_score": invest_score,
        "debt_ratio": round(debt_ratio * 100, 1),
        "debt_score": debt_score,
        "months_cover": round(months_cover, 1),
        "emergency_score": emergency_score
    }