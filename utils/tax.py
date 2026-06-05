def calculate_tax(income, deduction_80c=0.0, deduction_80d=0.0, deduction_hra=0.0):
    # Income represents Gross Annual Income
    
    # 1. New Regime Calculation (FY 2024-25 / FY 2025-26)
    std_deduction_new = 75000
    taxable_new = max(0.0, income - std_deduction_new)
    
    tax_new = 0.0
    # Slabs:
    # 0 - 3L: 0%
    # 3L - 7L: 5%
    # 7L - 10L: 10%
    # 10L - 12L: 15%
    # 12L - 15L: 20%
    # >15L: 30%
    if taxable_new <= 300000:
        tax_new = 0.0
    elif taxable_new <= 700000:
        tax_new = (taxable_new - 300000) * 0.05
    elif taxable_new <= 1000000:
        tax_new = 400000 * 0.05 + (taxable_new - 700000) * 0.10
    elif taxable_new <= 1200000:
        tax_new = 400000 * 0.05 + 300000 * 0.10 + (taxable_new - 1000000) * 0.15
    elif taxable_new <= 1500000:
        tax_new = 400000 * 0.05 + 300000 * 0.10 + 200000 * 0.15 + (taxable_new - 1200000) * 0.20
    else:
        tax_new = 400000 * 0.05 + 300000 * 0.10 + 200000 * 0.15 + 300000 * 0.20 + (taxable_new - 1500000) * 0.30
        
    # Rebate under Sec 87A for New Regime:
    if taxable_new <= 700000:
        tax_new = 0.0
        
    cess_new = tax_new * 0.04
    total_new = round(tax_new + cess_new, 2)
    
    # 2. Old Regime Calculation with custom deductions
    # Deductions cap logic:
    # 80C capped at 1.5 Lakhs (150,000)
    # 80D capped at 25,000 (standard limit)
    ded_80c = min(150000.0, float(deduction_80c))
    ded_80d = min(25000.0, float(deduction_80d))
    ded_hra = float(deduction_hra)
    
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
    total_old = round(tax_old + cess_old, 2)
    
    return {
        "gross_income": income,
        "deductions_applied": {
            "80c": ded_80c,
            "80d": ded_80d,
            "hra": ded_hra,
            "total": total_deductions_old
        },
        "new_regime": {
            "standard_deduction": std_deduction_new,
            "taxable_income": taxable_new,
            "base_tax": round(tax_new, 2),
            "cess": round(cess_new, 2),
            "total_tax": total_new
        },
        "old_regime": {
            "standard_deduction": std_deduction_old,
            "taxable_income": taxable_old,
            "base_tax": round(tax_old, 2),
            "cess": round(cess_old, 2),
            "total_tax": total_old
        },
        "recommended": "New Regime" if total_new < total_old else "Old Regime",
        "savings": round(abs(total_old - total_new), 2)
    }
