"""Tests for investment strategy recommendation."""
from __future__ import annotations

from valuation_workbench.models import ValuationCore, RatiosResult, DCFResult, ArchetypeResult
from valuation_workbench.valuation.strategy import recommend


def _mock_archetype(aid):
    return ArchetypeResult(
        archetype_id=aid, label_zh="x", label_en="x",
        description_zh="x", description_en="x", fit_score=0.5,
    )


def _mock_ratios():
    return RatiosResult(pe=10, pb=5, eps=2, pe_zh="", pe_en="", pb_zh="", pb_en="")


def _mock_dcf(upside=0.3):
    return DCFResult(
        five_year_pv=10, terminal_value=20, terminal_pv=12,
        fair_value=22, upside_pct=upside, wacc=0.15, g=0.05,
    )


def _mock_core():
    return ValuationCore(E=5, BV=5, P=20, g=0.05, beta=1.0, wacc=0.15)


def test_blue_chip_strategy():
    s = recommend(_mock_core(), _mock_ratios(), _mock_dcf(), _mock_archetype("blue_chip"))
    assert s.position == "LONG"
    assert s.hold_period == "LONG"


def test_distressed_strategy():
    s = recommend(_mock_core(), _mock_ratios(), _mock_dcf(-0.5), _mock_archetype("distressed"))
    assert s.position == "SHORT"
    assert s.conviction == "STRONG_SELL"


def test_improvements_count():
    s = recommend(_mock_core(), _mock_ratios(), _mock_dcf(), _mock_archetype("growth"))
    assert 3 <= len(s.improvements_zh) <= 5
    assert 3 <= len(s.improvements_en) <= 5


def test_strategy_serializable():
    s = recommend(_mock_core(), _mock_ratios(), _mock_dcf(), _mock_archetype("growth"))
    import json
    json.dumps(s.to_dict())
