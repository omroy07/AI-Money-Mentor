def calculate_sip(monthly, rate, years):
    r = rate / 100 / 12
    n = years * 12

    fv = monthly * (((1 + r)**n - 1) / r) * (1 + r)
    return round(fv, 2)
