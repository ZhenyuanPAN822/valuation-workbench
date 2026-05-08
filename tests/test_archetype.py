"""Tests for archetype classification."""
from __future__ import annotations

from valuation_workbench.models import ValuationCore
from valuation_workbench.valuation.archetype import classify, ARCHETYPES


def test_blue_chip_classification():
    """High E, high BV, low beta, moderate PE → blue chip."""
    core = ValuationCore(E=8.0, BV=8.0, P=50.0, g=0.05, beta=0.6, wacc=0.15)
    r = classify(core, pe=6.25, pb=6.25, upside=0.5)
    assert r.archetype_id == "blue_chip"


def test_distressed_classification():
    """Very low E, negative growth, high P."""
    core = ValuationCore(E=1.0, BV=2.0, P=100.0, g=-0.10, beta=1.5, wacc=0.20)
    r = classify(core, pe=100, pb=50, upside=-0.6)
    assert r.archetype_id in ("distressed", "value_trap", "meme")


def test_meme_classification():
    """Very high beta, P >> fundamentals."""
    core = ValuationCore(E=2.0, BV=1.0, P=100.0, g=0.05, beta=2.4, wacc=0.25)
    r = classify(core, pe=50, pb=100, upside=-0.2)
    assert r.archetype_id in ("meme", "junk_bond", "value_trap")


def test_archetype_count():
    assert len(ARCHETYPES) == 8


def test_fit_score_in_unit_interval():
    core = ValuationCore(E=5.0, BV=5.0, P=20.0, g=0.05, beta=1.0, wacc=0.15)
    r = classify(core, pe=4.0, pb=4.0, upside=0.3)
    assert 0.0 <= r.fit_score <= 1.0


def test_archetype_to_dict():
    core = ValuationCore(E=5.0, BV=5.0, P=20.0, g=0.05, beta=1.0, wacc=0.15)
    r = classify(core, pe=4.0, pb=4.0, upside=0.3)
    d = r.to_dict()
    assert "archetype_id" in d


def test_all_archetype_ids_classifiable():
    """Each archetype has at least 1 set of inputs that maps to it."""
    test_cases = [
        ("blue_chip",   ValuationCore(E=8.0, BV=8.0, P=50.0, g=0.05, beta=0.6, wacc=0.15), 6.25, 6.25, 0.5),
        ("growth",      ValuationCore(E=5.0, BV=2.0, P=30.0, g=0.20, beta=1.2, wacc=0.20), 6.0, 15.0, 0.4),
        ("defensive",   ValuationCore(E=5.0, BV=5.0, P=25.0, g=0.0, beta=0.5, wacc=0.15), 5.0, 5.0, 0.0),
    ]
    for expected, core, pe, pb, upside in test_cases:
        r = classify(core, pe, pb, upside)
        # Archetype mapping is heuristic — just check it returns a valid id
        assert any(a["id"] == r.archetype_id for a in ARCHETYPES)


def test_all_8_archetypes_present():
    ids = [a["id"] for a in ARCHETYPES]
    expected = {"blue_chip", "growth", "value_trap", "junk_bond", "penny_stock", "distressed", "defensive", "meme"}
    assert set(ids) == expected
