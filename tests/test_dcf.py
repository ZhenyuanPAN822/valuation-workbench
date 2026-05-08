"""Tests for DCF + sensitivity."""
from __future__ import annotations

from valuation_workbench.models import ValuationCore
from valuation_workbench.valuation.dcf import compute_dcf, sensitivity_table


def test_dcf_constant_e_g_zero():
    """E=1, g=0, WACC=10%, 5y annuity + Gordon TV.
    Annuity 5y: sum_{t=1..5} 1/1.1^t = 3.7908
    TV at year 5 with g=0: TV = 1/(0.1) = 10; PV = 10/1.1^5 = 6.2092
    fair_value = 3.7908 + 6.2092 ≈ 10.0
    """
    core = ValuationCore(E=1.0, BV=1.0, P=10.0, g=0.0, beta=1.0, wacc=0.10)
    r = compute_dcf(core, years=5)
    assert abs(r.fair_value - 10.0) < 0.5


def test_dcf_wacc_le_g_safety():
    """WACC ≤ g should not crash; safety guard kicks in."""
    core = ValuationCore(E=1.0, BV=1.0, P=10.0, g=0.20, beta=1.0, wacc=0.15)
    r = compute_dcf(core, years=5)
    # Should not raise; should return some finite value
    import math
    assert math.isfinite(r.fair_value)


def test_sensitivity_5x5():
    core = ValuationCore(E=2.0, BV=2.0, P=10.0, g=0.05, beta=1.0, wacc=0.15)
    s = sensitivity_table(core)
    assert len(s.g_grid) == 5
    assert len(s.wacc_grid) == 5
    assert len(s.table) == 5
    assert all(len(row) == 5 for row in s.table)


def test_dcf_upside_positive_when_fair_above_p():
    core = ValuationCore(E=10.0, BV=5.0, P=5.0, g=0.10, beta=1.0, wacc=0.20)
    r = compute_dcf(core)
    assert r.upside_pct > 0


def test_dcf_upside_negative_when_fair_below_p():
    core = ValuationCore(E=0.5, BV=1.0, P=100.0, g=0.0, beta=1.0, wacc=0.20)
    r = compute_dcf(core)
    assert r.upside_pct < 0


def test_dcf_returns_dict_serializable():
    core = ValuationCore(E=1.0, BV=1.0, P=10.0, g=0.05, beta=1.0, wacc=0.15)
    r = compute_dcf(core)
    d = r.to_dict()
    import json
    json.dumps(d)
