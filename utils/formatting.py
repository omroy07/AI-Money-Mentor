"""Indian-style number formatting (lakh and crore grouping)."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

RUPEE = "₹"
LAKH = Decimal("100000")
CRORE = Decimal("10000000")


def _to_decimal(amount):
    if amount is None or isinstance(amount, bool):
        return Decimal(0)
    try:
        value = Decimal(str(amount).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return Decimal(0)
    return value if value.is_finite() else Decimal(0)


def _group_indian(digits):
    """Group a string of digits as 12,34,567."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def _quantize(value, decimals):
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def format_inr(amount, compact=False, decimals=2):
    """Format an amount in rupees with Indian digit grouping.

    format_inr(1234567.5)                -> "₹12,34,567.50"
    format_inr(1234567.5, compact=True)  -> "₹12.3 L"
    format_inr(12345678, compact=True)   -> "₹1.2 Cr"
    None and unparseable values are treated as 0.
    """
    value = _to_decimal(amount)
    sign = "-" if value < 0 else ""
    value = abs(value)

    if compact and value >= LAKH:
        if value >= CRORE:
            scaled, unit = _quantize(value / CRORE, 1), "Cr"
        else:
            scaled, unit = _quantize(value / LAKH, 1), "L"
            if scaled >= 100:
                scaled, unit = _quantize(value / CRORE, 1), "Cr"
        return f"{sign}{RUPEE}{scaled} {unit}"

    rounded = _quantize(value, decimals)
    whole, _, frac = f"{rounded:f}".partition(".")
    text = _group_indian(whole) + (f".{frac}" if frac else "")
    if rounded == 0:
        sign = ""
    return f"{sign}{RUPEE}{text}"
