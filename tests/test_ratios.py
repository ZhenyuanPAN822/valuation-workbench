"""Tests for PE / PB / EPS."""
from __future__ import annotations

from valuation_workbench.models import ValuationCore
from valuation_workbench.valuation.ratios import compute_ratios


def test_pe_basic():
    core = ValuationCore(E=5.0, BV=10.0, P=50.0, g=0.05, beta=1.0, wacc=0.15)
    r = compute_ratios(core)
    assert abs(r.pe - 10.0) < 0.01
    assert abs(r.pb - 5.0) < 0.01
    assert r.eps == 5.0


def test_pe_extreme_premium():
    core = ValuationCore(E=1.0, BV=1.0, P=200.0, g=0.05, beta=1.0, wacc=0.15)
    r = compute_ratios(core)
    assert "extreme" in r.pe_en.lower() or "高估" in r.pe_zh


def test_pb_below_book():
    core = ValuationCore(E=5.0, BV=20.0, P=10.0, g=0.05, beta=1.0, wacc=0.15)
    r = compute_ratios(core)
    assert r.pb < 1.0
    assert "below" in r.pb_en.lower() or "折价" in r.pb_zh


def test_zero_e_no_crash():
    """Zero E should not divide-by-zero."""
    core = ValuationCore(E=0.0, BV=1.0, P=10.0, g=0.0, beta=1.0, wacc=0.15)
    r = compute_ratios(core)
    import math
    assert math.isfinite(r.pe)
