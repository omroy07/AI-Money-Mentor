import sys
import json
import pytest
from unittest.mock import MagicMock

sys.modules['yfinance'] = MagicMock()
sys.modules['groq'] = MagicMock()
sys.modules['pdfplumber'] = MagicMock()
sys.modules['scipy.stats'] = MagicMock()
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()
sys.modules['apscheduler.triggers'] = MagicMock()
sys.modules['apscheduler.triggers.cron'] = MagicMock()
sys.modules['flask_socketio'] = MagicMock()
sys.modules['flask_mail'] = MagicMock()
sys.modules['flask_login'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.optimize'] = MagicMock()

from utils.fire_planner import FIREPlanner


# ── Fixture helpers ────────────────────────────────────────────────────────

def _make_planner(**overrides):
    kwargs = dict(
        current_age=30,
        retirement_age=45,
        annual_expenses=500000,
        current_corpus=1000000,
        monthly_savings=30000,
        return_mean=0.10,
        return_std=0.15,
        inflation_rate=0.06,
        withdrawal_rate=0.04,
        life_expectancy=85,
    )
    kwargs.update(overrides)
    return FIREPlanner(**kwargs)


# ── Lean / Fat ────────────────────────────────────────────────────────────

def test_lean_fire_half_expenses():
    p = _default_planner()
    proj = p.compute_lean_fat_projections()
    assert proj['lean']['name'] == 'Lean FIRE'
    assert proj['lean']['annual_expenses'] == 250000.0
    assert proj['lean']['multiplier_of_expenses'] == 12.5


def test_regular_fire_matches_expenses():
    p = _default_planner()
    proj = p.compute_lean_fat_projections()
    assert proj['regular']['annual_expenses'] == 500000
    assert proj['regular']['multiplier_of_expenses'] == 25.0


def test_fat_fire_double_expenses():
    p = _default_planner()
    proj = p.compute_lean_fat_projections()
    assert proj['fat']['name'] == 'Fat FIRE'
    assert proj['fat']['annual_expenses'] == 750000.0
    assert proj['fat']['multiplier_of_expenses'] == 37.5


def test_lean_fat_corpus_scale_with_withdrawal_rate():
    p = _default_planner(withdrawal_rate=0.05)
    proj = p.compute_lean_fat_projections()
    assert proj['regular']['target_corpus'] == pytest.approx(10000000.0)  # 20x expenses
    assert proj['lean']['target_corpus'] == pytest.approx(5000000.0)


# ── Timeline projection ───────────────────────────────────────────────────

def test_timeline_generates_all_ages():
    p = _default_planner(life_expectancy=90)
    tl = p.get_timeline_projection(iterations=50)
    assert tl['ages'][0] == 30
    assert tl['ages'][-1] == 90
    assert len(tl['ages']) == 61


def test_timeline_accumulation_phase_first():
    p = _default_planner()
    tl = p.get_timeline_projection(iterations=50)
    phases = tl['phases']
    acc_end = p.years_to_retirement
    assert all(ph == 'accumulation' for ph in phases[:acc_end])
    assert all(ph == 'retirement' for ph in phases[acc_end:])


def test_timeline_percentiles_are_ordered():
    p = _default_planner()
    tl = p.get_timeline_projection(iterations=100)
    pct = tl['percentiles']
    for idx in range(len(pct['5th'])):
        assert pct['5th'][idx] <= pct['50th'][idx] <= pct['95th'][idx] or pct['5th'][idx] == 0.0


def test_timeline_depletion_age_is_zero_median():
    p = _default_planner(life_expectancy=120)
    tl = p.get_timeline_projection(iterations=50)
    if tl['depletion_age'] is not None:
        idx = tl['depletion_age'] - p.current_age
        assert tl['percentiles']['50th'][idx] == 0.0


def test_depletion_age_none_when_corpus_survives():
    p = _default_planner(
        current_age=30, retirement_age=35, annual_expenses=100000,
        current_corpus=50000000, monthly_savings=100000,
        life_expectancy=60,
    )
    tl = p.get_timeline_projection(iterations=100)
    assert tl['depletion_age'] is None


def test_target_corpus_follows_withdrawal_formula():
    p = _default_planner(withdrawal_rate=0.05)
    assert p.target_corpus == 10000000.0
    p2 = FIREPlanner(30, 45, 800000, 0, withdrawal_rate=0.04, life_expectancy=85)
    assert p2.target_corpus == 20000000.0


def test_plan_summary_includes_new_fields():
    p = _default_planner()
    summary = p.get_plan_summary()
    assert 'lean_fat_projections' in summary
    assert 'timeline_projection' in summary
    assert 'life_expectancy' in summary['input_summary']
    assert 'withdrawal_rate' in summary['input_summary']
    assert summary['input_summary']['withdrawal_rate'] == 0.04
    assert summary['input_summary']['life_expectancy'] == 85


# ── Edge cases ────────────────────────────────────────────────────────────

def test_zero_withdrawal_uses_fallback():
    p = FIREPlanner(30, 45, 500000, 1000000, withdrawal_rate=0, life_expectancy=85)
    assert p.target_corpus == 12500000.0


def test_constructed_invariant_nonnegative():
    p = _default_planner()
    assert p.years_to_retirement >= 0
    assert p.retirement_years >= 0
    assert p.target_corpus >= 0