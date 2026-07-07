from datetime import datetime
from typing import Dict

def calculate_money_score(income, expenses, savings, investments, debt, emergency_fund):
    """Backwards-compatible numeric Money Score (0-100)."""


    score = 0

    # 1. Savings Rate (30)
    savings_rate = savings / income if income > 0 else 0.0
    if savings_rate >= 0.3:
        score += 30
    elif savings_rate >= 0.2:
        score += 20
    else:
        score += 10

    # 2. Investment Rate (25)
    invest_rate = investments / income if income > 0 else 0.0
    if invest_rate >= 0.2:
        score += 25
    elif invest_rate >= 0.1:
        score += 15
    else:
        score += 5

    # 3. Debt Ratio (25)
    debt_ratio = debt / income if income > 0 else (1.0 if debt > 0 else 0.0)
    if debt_ratio <= 0.2:
        score += 25
    elif debt_ratio <= 0.4:
        score += 15
    else:
        score += 5

    # 4. Emergency Fund (20)
    months_cover = emergency_fund / expenses if expenses > 0 else (12.0 if emergency_fund > 0 else 0.0)
    if months_cover >= 6:
        score += 20
    elif months_cover >= 3:
        score += 10
    else:
        score += 5

    return round(score)


from typing import Dict, List, Tuple


def _component_status_by_score(score: int, tiers: List[Tuple[int, int]]):
    """Return a human label based on which tier bucket matched.

    tiers: list of (min_points_inclusive, status_label)
    """
    for min_points, label in tiers:
        if score >= min_points:
            return label
    return 'fair'


def calculate_money_score_breakdown(income, expenses, savings, investments, debt, emergency_fund) -> Dict:
    """Return a detailed Financial Health breakdown for UI deep-dive."""

    income = float(income or 0)
    expenses = float(expenses or 0)
    savings = float(savings or 0)
    investments = float(investments or 0)
    debt = float(debt or 0)
    emergency_fund = float(emergency_fund or 0)

    # Derived metrics
    savings_rate = savings / income if income > 0 else 0.0
    invest_rate = investments / income if income > 0 else 0.0
    debt_ratio = debt / income if income > 0 else (1.0 if debt > 0 else 0.0)
    months_cover = emergency_fund / expenses if expenses > 0 else (12.0 if emergency_fund > 0 else 0.0)

    # Tiering rules (match existing calculate_money_score thresholds)
    def savings_component():
        if savings_rate >= 0.3:
            score = 30
            tier = '>= 30%'
        elif savings_rate >= 0.2:
            score = 20
            tier = '20%–29%'
        else:
            score = 10
            tier = '< 20%'

        tips = [
            'If feasible, automate savings the day you get paid.',
            'Aim to increase savings rate by 2–5 percentage points over the next 8–12 weeks.',
        ]
        if savings_rate < 0.2:
            tips.insert(0, 'Start by reducing 1 non-essential expense category (small wins matter).')
        return {
            'key': 'savings_rate',
            'label': 'Savings Rate',
            'weight': 30,
            'your_value': round(savings_rate * 100, 2),
            'unit': '% of income',
            'tier': tier,
            'score': score,
            'max_score': 30,
            'interpretation': 'excellent' if score == 30 else 'good' if score == 20 else 'needs_improvement',
            'tips': tips,
            'calculation': 'Savings Rate = Monthly Savings / Monthly Income'
        }

    def investment_component():
        if invest_rate >= 0.2:
            score = 25
            tier = '>= 20%'
        elif invest_rate >= 0.1:
            score = 15
            tier = '10%–19%'
        else:
            score = 5
            tier = '< 10%'

        tips = [
            'Increase investment contributions gradually (e.g., +1% of income per month).',
            'Prioritize diversified, low-cost index funds/ETFs for long-term growth.',
        ]
        if invest_rate < 0.1:
            tips.insert(0, 'Set an “investment minimum” (even if small) so you keep the habit consistent.')
        return {
            'key': 'investment_rate',
            'label': 'Investment Rate',
            'weight': 25,
            'your_value': round(invest_rate * 100, 2),
            'unit': '% of income',
            'tier': tier,
            'score': score,
            'max_score': 25,
            'interpretation': 'excellent' if score == 25 else 'good' if score == 15 else 'needs_improvement',
            'tips': tips,
            'calculation': 'Investment Rate = Monthly Investments / Monthly Income'
        }

    def debt_component():
        # Lower is better
        if debt_ratio <= 0.2:
            score = 25
            tier = '<= 20%'
        elif debt_ratio <= 0.4:
            score = 15
            tier = '20%–40%'
        else:
            score = 5
            tier = '> 40%'

        tips = [
            'Consider refinancing to reduce interest cost (if available).',
            'Choose a payoff order (high-interest first) to reduce interest drag.',
        ]
        if debt_ratio > 0.4:
            tips.insert(0, 'Reduce debt payments pressure: focus on paying down the highest-interest loan first.')
        elif debt_ratio > 0.2:
            tips.insert(0, 'Try extra principal payments whenever cashflow allows.')

        return {
            'key': 'debt_ratio',
            'label': 'Debt-to-Income Ratio (DTI)',
            'weight': 25,
            'your_value': round(debt_ratio * 100, 2),
            'unit': '% of income',
            'tier': tier,
            'score': score,
            'max_score': 25,
            'interpretation': 'excellent' if score == 25 else 'good' if score == 15 else 'needs_improvement',
            'tips': tips,
            'calculation': 'Debt Ratio = Total Debt / Monthly Income (proxy used by this scorer)'
        }

    def emergency_component():
        # Higher is better
        if months_cover >= 6:
            score = 20
            tier = '>= 6 months'
        elif months_cover >= 3:
            score = 10
            tier = '3–5 months'
        else:
            score = 5
            tier = '< 3 months (or none)'

        tips = [
            'Keep emergency funds in low-volatility options (e.g., savings/overnight funds).',
            'Set a monthly top-up amount until you reach 3 months, then 6 months.',
        ]
        if months_cover < 3 and emergency_fund > 0:
            tips.insert(0, 'Aim to double your emergency fund over the next 6–9 months by redirecting small surpluses.')
        elif months_cover == 0:
            tips.insert(0, 'Start with a “starter buffer” (₹25k–₹50k) before optimizing other goals.')

        return {
            'key': 'emergency_coverage',
            'label': 'Emergency Fund Coverage',
            'weight': 20,
            'your_value': round(months_cover, 2),
            'unit': 'months of expenses',
            'tier': tier,
            'score': score,
            'max_score': 20,
            'interpretation': 'excellent' if score == 20 else 'good' if score == 10 else 'needs_improvement',
            'tips': tips,
            'calculation': 'Months Cover = Emergency Fund / Monthly Expenses (special case: expenses=0)'
        }

    components = [
        savings_component(),
        investment_component(),
        debt_component(),
        emergency_component(),
    ]

    score = round(sum(c['score'] for c in components))
    if score >= 80:
        status = 'Excellent 💚'
        grade = 'A'
    elif score >= 60:
        status = 'Good 👍'
        grade = 'B'
    elif score >= 40:
        status = 'Average ⚠️'
        grade = 'C'
    else:
        status = 'Needs Improvement ❌'
        grade = 'D'

    # Anonymous peer benchmarks (simple, deterministic approximations)
    peer_benchmarks = {
        'savings_rate': 0.23,      # 23%
        'investment_rate': 0.12,   # 12%
        'debt_ratio': 0.32,        # 32%
        'emergency_coverage': 4.0  # 4 months
    }

    key_to_peer = {
        'savings_rate': peer_benchmarks['savings_rate'] * 100,
        'investment_rate': peer_benchmarks['investment_rate'] * 100,
        'debt_ratio': peer_benchmarks['debt_ratio'] * 100,
        'emergency_coverage': peer_benchmarks['emergency_coverage']
    }

    for c in components:
        peer_val = key_to_peer.get(c['key'], None)
        c['peer_benchmark_value'] = peer_val
        c['peer_benchmark_text'] = None
        if peer_val is not None:
            if c['unit'] == '% of income':
                c['peer_benchmark_text'] = f"Peers ~ {round(peer_val, 2)}%"
            else:
                c['peer_benchmark_text'] = f"Peers ~ {round(peer_val, 2)} months"

    return {
        'score': score,
        'status': status,
        'grade': grade,
        'components': components,
        'generated_at': datetime.utcnow().isoformat() if 'datetime' in globals() else None
    }
