def calculate_tax(income, deductions_80c=0.0, deductions_80d=0.0, hra=0.0):
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
    # Under New Regime, if taxable income <= 700,000, tax rebate equals tax payable (i.e. zero tax)
    if taxable_new <= 700000:
        tax_new = 0.0
        
    cess_new = tax_new * 0.04
    total_new = round(tax_new + cess_new, 2)
    
    # 2. Old Regime Calculation
    std_deduction_old = 50000
    # Apply deductions under 80C (max 1.5L), 80D (max 25k), and HRA
    allowed_80c = min(float(deductions_80c or 0.0), 150000.0)
    allowed_80d = min(float(deductions_80d or 0.0), 25000.0)
    allowed_hra = float(hra or 0.0)
    
    total_deductions = std_deduction_old + allowed_80c + allowed_80d + allowed_hra
    taxable_old = max(0.0, income - total_deductions)
    
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
    # Under Old Regime, if taxable income <= 500,000, rebate is 100% of tax up to 12500
    if taxable_old <= 500000:
        tax_old = 0.0
        
    cess_old = tax_old * 0.04
    total_old = round(tax_old + cess_old, 2)
    
    return {
        "gross_income": income,
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
            "total_tax": total_old,
            "deductions_80c_applied": allowed_80c,
            "deductions_80d_applied": allowed_80d,
            "hra_applied": allowed_hra,
            "total_deductions": total_deductions
        },
        "recommended": "New Regime" if total_new < total_old else "Old Regime",
        "savings": round(abs(total_old - total_new), 2)
    }
