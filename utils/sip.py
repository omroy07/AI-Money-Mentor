def calculate_sip(monthly, rate, years, inflation_rate=0.0):
    n = years * 12
    if rate == 0:
        fv = monthly * n
    else:
        r = rate / 100 / 12
        fv = monthly * (((1 + r)**n - 1) / r) * (1 + r)
    
    if inflation_rate > 0:
        fv_adjusted = fv / ((1 + (inflation_rate / 100)) ** years)
        return {
            "nominal_value": round(fv, 2),
            "inflation_adjusted_value": round(fv_adjusted, 2),
            "inflation_applied": inflation_rate
        }
        
    return {
        "nominal_value": round(fv, 2),
        "inflation_adjusted_value": round(fv, 2),
        "inflation_applied": 0.0
    }

