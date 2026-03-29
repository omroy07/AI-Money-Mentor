def calculate_tax(income):
    if income < 500000:
        return 0
    elif income < 1000000:
        return income * 0.1
    else:
        return income * 0.2