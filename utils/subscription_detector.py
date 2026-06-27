import json
from datetime import datetime, timedelta, date
from typing import List, Dict

from models import db, RecurringExpense, Expense

def detect_subscriptions(transactions: List[Expense]) -> List[Dict]:
    """Detect subscription-like recurring expenses.
    Returns a list of dicts with subscription details.
    """
    patterns = {}
    for exp in transactions:
        key = f"{exp.merchant or 'Unknown'}_{exp.category}"
        if key not in patterns:
            patterns[key] = {'merchant': exp.merchant or 'Unknown', 'category': exp.category, 'amounts': [], 'dates': []}
        patterns[key]['amounts'].append(exp.amount)
        # Expect date stored as string; convert to date
        try:
            exp_date = datetime.strptime(exp.date, "%Y-%m-%d").date()
        except Exception:
            continue
        patterns[key]['dates'].append(exp_date)
    detected = []
    for key, data in patterns.items():
        if len(data['amounts']) >= 2:
            avg_amount = sum(data['amounts']) / len(data['amounts'])
            variation = max([abs(a - avg_amount) / avg_amount for a in data['amounts']])
            if variation <= 0.15:  # allow slightly higher variance
                sorted_dates = sorted(data['dates'])
                if len(sorted_dates) >= 2:
                    diffs = [(sorted_dates[i] - sorted_dates[i-1]).days for i in range(1, len(sorted_dates))]
                    avg_diff = sum(diffs) / len(diffs)
                    if 28 <= avg_diff <= 31:
                        frequency = 'monthly'
                    elif 7 <= avg_diff <= 8:
                        frequency = 'weekly'
                    elif 85 <= avg_diff <= 95:
                        frequency = 'quarterly'
                    elif 355 <= avg_diff <= 370:
                        frequency = 'yearly'
                    else:
                        frequency = 'unknown'
                    next_due = sorted_dates[-1] + timedelta(days=round(avg_diff))
                    detected.append({
                        'merchant': data['merchant'],
                        'category': data['category'],
                        'amount': round(avg_amount, 2),
                        'frequency': frequency,
                        'next_due': next_due.isoformat(),
                        'confidence': 'high' if len(data['amounts']) >= 3 else 'medium'
                    })
    return detected

def run_detection():
    """Run subscription detection on recent expenses and persist results.
    Newly detected subscriptions are added to RecurringExpense with is_subscription=True and status='pending'.
    """
    cutoff_date = date.today() - timedelta(days=60)
    expenses = Expense.query.filter(Expense.date >= cutoff_date.isoformat()).all()
    detected = detect_subscriptions(expenses)
    for sub in detected:
        exists = RecurringExpense.query.filter_by(
            merchant=sub['merchant'],
            amount=sub['amount'],
            category=sub['category'],
            next_due_date=datetime.strptime(sub['next_due'], "%Y-%m-%d").date()
        ).first()
        if not exists:
            rec = RecurringExpense(
                amount=sub['amount'],
                category=sub['category'],
                merchant=sub['merchant'],
                frequency=sub['frequency'],
                start_date=datetime.strptime(sub['next_due'], "%Y-%m-%d").date(),
                next_due_date=datetime.strptime(sub['next_due'], "%Y-%m-%d").date(),
                is_subscription=True,
                status='pending',
                auto_add=False
            )
            db.session.add(rec)
    db.session.commit()
    return {'detected': detected, 'count': len(detected)}
