"""Tests for utils.fx rate sources (RBI for INR pairs, open.er-api, ECB fallback).

HTTP is mocked; no network access.
"""
import json
from unittest.mock import patch

import pytest

from app import app, db
from models import FxRateCache
from utils import fx

RBI_PAYLOAD = {
    "bank": "rbi",
    "rate_date": "2026-10-30",
    "rates": [
        {"base": "USD", "quote": "INR", "type": "reference", "value": 95.2492},
        {"base": "EUR", "quote": "INR", "type": "reference", "value": 106.5451},
        {"base": "GBP", "quote": "INR", "type": "reference", "value": 127.6015},
        {"base": "JPY", "quote": "INR", "type": "reference", "value": 0.6045},
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_urlopen(routes):
    """routes: list of (url_substring, payload or Exception)."""
    calls = []

    def _open(req, timeout=None):
        url = req.full_url
        calls.append(url)
        for needle, result in routes:
            if needle in url:
                if isinstance(result, Exception):
                    raise result
                return FakeResponse(result)
        raise OSError(f"unexpected URL {url}")

    _open.calls = calls
    return _open


@pytest.fixture
def ctx():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def test_inr_pair_uses_rbi_reference_rate(ctx):
    opener = fake_urlopen([("central-bank/rbi", RBI_PAYLOAD)])
    with patch("utils.fx.urllib.request.urlopen", opener):
        assert fx.get_rate("USD", "INR") == pytest.approx(95.2492)
    assert len(opener.calls) == 1
    cached = FxRateCache.query.filter_by(from_currency="USD", to_currency="INR").first()
    assert cached.rate == pytest.approx(95.2492)


def test_inr_to_foreign_is_inverted(ctx):
    opener = fake_urlopen([("central-bank/rbi", RBI_PAYLOAD)])
    with patch("utils.fx.urllib.request.urlopen", opener):
        assert fx.get_rate("INR", "EUR") == pytest.approx(1 / 106.5451)


def test_currency_rbi_lacks_falls_back_to_open_er_api(ctx):
    opener = fake_urlopen([
        ("central-bank/rbi", RBI_PAYLOAD),
        ("open.er-api.com/v6/latest/CAD", {"result": "success", "rates": {"INR": 69.1}}),
    ])
    with patch("utils.fx.urllib.request.urlopen", opener):
        assert fx.get_rate("CAD", "INR") == pytest.approx(69.1)


def test_rbi_error_falls_back_to_open_er_api(ctx):
    opener = fake_urlopen([
        ("central-bank/rbi", OSError("down")),
        ("open.er-api.com/v6/latest/USD", {"result": "success", "rates": {"INR": 95.0}}),
    ])
    with patch("utils.fx.urllib.request.urlopen", opener):
        assert fx.get_rate("USD", "INR") == pytest.approx(95.0)


def test_non_inr_pair_skips_rbi(ctx):
    opener = fake_urlopen([
        ("open.er-api.com/v6/latest/USD", {"result": "success", "rates": {"EUR": 0.9}}),
    ])
    with patch("utils.fx.urllib.request.urlopen", opener):
        assert fx.get_rate("USD", "EUR") == pytest.approx(0.9)
    assert not any("central-bank/rbi" in u for u in opener.calls)


def test_ecb_fallback_when_open_er_api_fails(ctx):
    opener = fake_urlopen([
        ("open.er-api.com", OSError("down")),
        ("allratestoday.com/api/open/latest/USD", {"base": "USD", "rates": {"EUR": 0.86}}),
    ])
    with patch("utils.fx.urllib.request.urlopen", opener):
        assert fx.get_rate("USD", "EUR") == pytest.approx(0.86)


def test_all_sources_down_uses_offline_rates(ctx):
    opener = fake_urlopen([])  # every URL raises
    with patch("utils.fx.urllib.request.urlopen", opener):
        assert fx.get_rate("USD", "INR") == pytest.approx(fx.OFFLINE_RATES["USD"])
