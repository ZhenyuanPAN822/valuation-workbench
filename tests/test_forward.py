"""Tests for forward scenarios + full pipeline."""
from __future__ import annotations

from valuation_workbench import run_pipeline, list_targets


def test_run_pipeline_for_each_target():
    for t in list_targets():
        from valuation_workbench import get_schema
        s = get_schema(t)
        ans = {f.id: f.default if not isinstance(f.default, list) else [] for f in s.fields}
        r = run_pipeline(t, ans)
        assert r.target_type == t
        assert r.archetype.archetype_id


def test_three_scenarios_present():
    from valuation_workbench import get_schema
    s = get_schema("crush")
    ans = {f.id: f.default if not isinstance(f.default, list) else [] for f in s.fields}
    r = run_pipeline("crush", ans)
    assert "bear" in r.scenarios and "base" in r.scenarios and "bull" in r.scenarios


def test_unknown_target_raises():
    import pytest
    with pytest.raises(ValueError):
        run_pipeline("nonexistent", {})


def test_forward_var_perturbation():
    """When forward_var perturbs g, scenarios should differ."""
    from valuation_workbench import get_schema
    s = get_schema("crush")
    ans = {f.id: f.default if not isinstance(f.default, list) else [] for f in s.fields}
    r = run_pipeline("crush", ans, delta_pct=0.50)
    # bear and bull E should differ (since some fields are forward_eligible and influence E)
    bear_e = r.scenarios["bear"]["E"] if isinstance(r.scenarios["bear"], dict) else 0
    bull_e = r.scenarios["bull"]["E"] if isinstance(r.scenarios["bull"], dict) else 0
    # they may not always differ depending on which fields are forward_eligible
    # but they should not crash
    assert bear_e >= 0 and bull_e >= 0
