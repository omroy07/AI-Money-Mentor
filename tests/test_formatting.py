import json
import shutil
import subprocess
from pathlib import Path

import pytest

from utils.formatting import format_inr

ROOT = Path(__file__).resolve().parent.parent


def test_basic_grouping():
    assert format_inr(1234567.5) == "₹12,34,567.50"
    assert format_inr(999) == "₹999.00"
    assert format_inr(1000) == "₹1,000.00"
    assert format_inr(100000) == "₹1,00,000.00"
    assert format_inr(12345678) == "₹1,23,45,678.00"


def test_zero_and_none():
    assert format_inr(0) == "₹0.00"
    assert format_inr(None) == "₹0.00"
    assert format_inr("abc") == "₹0.00"
    assert format_inr(float("nan")) == "₹0.00"


def test_negative():
    assert format_inr(-1234567.5) == "-₹12,34,567.50"
    assert format_inr(-0.001) == "₹0.00"


def test_large_values():
    assert format_inr(98765432101) == "₹98,76,54,32,101.00"
    assert format_inr(10**12, decimals=0) == "₹10,00,00,00,00,000"


def test_rounding_half_up():
    assert format_inr(2.675) == "₹2.68"
    assert format_inr(0.125, decimals=2) == "₹0.13"
    assert format_inr(1234.5, decimals=0) == "₹1,235"


def test_compact():
    assert format_inr(1234567.5, compact=True) == "₹12.3 L"
    assert format_inr(12345678, compact=True) == "₹1.2 Cr"
    assert format_inr(99999, compact=True) == "₹99,999.00"
    assert format_inr(100000, compact=True) == "₹1.0 L"
    assert format_inr(9999999, compact=True) == "₹1.0 Cr"
    assert format_inr(-250000, compact=True) == "-₹2.5 L"


def test_jinja_filter_registered():
    from app import app

    assert app.jinja_env.filters["inr"](1234567.5) == "₹12,34,567.50"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_js_matches_python():
    samples = [0, 5, 999, 1000, 12345.678, 100000, 1234567.5, 9999999, 12345678, -1234567.5, None]
    script = (
        "global.window = global;"
        f"require({json.dumps(str(ROOT / 'static' / 'scripts' / 'format_inr.js'))});"
        f"const s = {json.dumps(samples)};"
        "const out = [];"
        "for (const v of s) { out.push(formatINR(v)); out.push(formatINR(v, {compact: true})); }"
        "console.log(JSON.stringify(out));"
    )
    res = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True
    )
    js = json.loads(res.stdout)
    py = []
    for v in samples:
        py.append(format_inr(v))
        py.append(format_inr(v, compact=True))
    assert js == py
