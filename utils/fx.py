import urllib.request
import json
import datetime
from models import db, FxRateCache

OFFLINE_RATES = {
    'INR': 1.0,
    'USD': 83.5,
    'EUR': 90.5,
    'GBP': 106.0,
    'JPY': 0.53,
    'CAD': 61.5,
    'AUD': 55.0,
    'AED': 22.7,
    'SGD': 62.0
}

# Keyless AllRatesToday endpoints (no API key needed).
# RBI reference rate (FBIL) for INR pairs: USD, EUR, GBP, JPY, AED, IDR.
RBI_RATES_URL = "https://allratestoday.com/api/open/central-bank/rbi"
# ECB reference rates, used as a last resort when open.er-api is unavailable.
ECB_LATEST_URL = "https://allratestoday.com/api/open/latest/{base}"
OPEN_ER_API_URL = "https://open.er-api.com/v6/latest/{base}"


def _get_json(url: str):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode())


def _fetch_rbi_rate(from_currency: str, to_currency: str):
    """Official RBI reference rate for INR pairs, or None if RBI does not publish it."""
    if 'INR' not in (from_currency, to_currency):
        return None
    try:
        data = _get_json(RBI_RATES_URL)
        inr_per_unit = {
            r['base']: float(r['value'])
            for r in data.get('rates', [])
            if r.get('quote') == 'INR' and r.get('value')
        }
        if to_currency == 'INR':
            return inr_per_unit.get(from_currency)
        if to_currency in inr_per_unit:
            return 1.0 / inr_per_unit[to_currency]
    except Exception as e:
        print(f"[FX RBI Fetch Error] {e}")
    return None


def _fetch_open_er_api_rate(from_currency: str, to_currency: str):
    try:
        data = _get_json(OPEN_ER_API_URL.format(base=from_currency))
        if data.get("result") == "success" and "rates" in data:
            rate = data["rates"].get(to_currency)
            if rate is not None:
                return float(rate)
    except Exception as e:
        print(f"[FX API Fetch Error] {e}")
    return None


def _fetch_ecb_rate(from_currency: str, to_currency: str):
    try:
        data = _get_json(ECB_LATEST_URL.format(base=from_currency))
        rate = data.get("rates", {}).get(to_currency)
        if rate is not None:
            return float(rate)
    except Exception as e:
        print(f"[FX ECB Fetch Error] {e}")
    return None


def _save_to_cache(from_currency: str, to_currency: str, rate: float, now):
    try:
        existing = FxRateCache.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency
        ).first()
        if existing:
            existing.rate = rate
            existing.updated_at = now
        else:
            db.session.add(FxRateCache(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                updated_at=now
            ))
        db.session.commit()
    except Exception as db_err:
        db.session.rollback()
        print(f"[FX Cache Save Error] {db_err}")


def get_rate(from_currency: str, to_currency: str = 'INR') -> float:
    """Fetch the exchange rate from from_currency to to_currency.
    
    Tries DB cache first, then the RBI reference rate (INR pairs), open.er-api
    and the ECB reference rate, and falls back to older cache or offline rates.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    
    if from_currency == to_currency:
        return 1.0
        
    # Check if DB cache has a recent rate (less than 12 hours old)
    now = datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(hours=12)
    
    try:
        cached = FxRateCache.query.filter(
            FxRateCache.from_currency == from_currency,
            FxRateCache.to_currency == to_currency,
            FxRateCache.updated_at >= cutoff
        ).first()
        if cached:
            return cached.rate
    except Exception as e:
        print(f"[FX Cache Check Error] {e}")

    # Fetch from APIs, most authoritative first
    for fetch in (_fetch_rbi_rate, _fetch_open_er_api_rate, _fetch_ecb_rate):
        rate = fetch(from_currency, to_currency)
        if rate:
            _save_to_cache(from_currency, to_currency, rate, now)
            return float(rate)
    print("[FX] All rate APIs failed - falling back to older cache or offline rate")

    # If API fails, try to get ANY cached rate, even if older than 12 hours
    try:
        any_cached = FxRateCache.query.filter_by(
            from_currency=from_currency,
            to_currency=to_currency
        ).first()
        if any_cached:
            return any_cached.rate
    except Exception as e:
        pass

    # Offline fallback logic
    if from_currency in OFFLINE_RATES and to_currency in OFFLINE_RATES:
        inr_per_from = OFFLINE_RATES[from_currency]
        inr_per_to = OFFLINE_RATES[to_currency]
        return inr_per_from / inr_per_to

    return 1.0

def convert_to_base(amount: float, from_currency: str) -> float:
    """Convert amount in from_currency to INR (base currency)."""
    if not amount:
        return 0.0
    rate = get_rate(from_currency, 'INR')
    return amount * rate
