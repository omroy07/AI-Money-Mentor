def calculate_tax(income):
    if income <= 0:
        return 0

    # India New Tax Regime slabs (FY 2024-25)
    slabs = [
        (300_000, 0.00),
        (400_000, 0.05),   # 3L – 7L
        (300_000, 0.10),   # 7L – 10L
        (200_000, 0.15),   # 10L – 12L
        (300_000, 0.20),   # 12L – 15L
    ]

    tax = 0
    remaining = income
    for limit, rate in slabs:
        if remaining <= 0:
            break
        taxable = min(remaining, limit)
        tax += taxable * rate
        remaining -= taxable
    if remaining > 0:
        tax += remaining * 0.30

    # Section 87A rebate: zero tax if income ≤ 7,00,000
    if income <= 700_000:
        tax = 0

    # 4% health & education cess
    return round(tax * 1.04, 2)
