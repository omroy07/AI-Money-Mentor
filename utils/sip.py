def calculate_sip(monthly, rate, years):
    n = years * 12

    if rate == 0:
        return round(monthly * n, 2)

    r = rate / 100 / 12
    fv = monthly * (((1 + r) ** n - 1) / r) * (1 + r)
    return round(fv, 2)
