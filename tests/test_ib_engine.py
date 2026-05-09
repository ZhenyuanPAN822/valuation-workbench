"""IB-engine tests: aggregation, 3-stage DCF, multiples, asset, blend, MC."""
from __future__ import annotations

import pytest

from valuation_workbench import (
    get_fallback_schema, run_pipeline_ib, IBInputs,
    aggregate_ib_inputs, compute_dcf_3stage, compute_multiples,
    compute_asset, blend_valuations, monte_carlo,
)


def _ib_default():
    s = get_fallback_schema()
    ans = {f.id: f.default for f in s.fields}
    return s, ans, aggregate_ib_inputs(s, ans)


def test_aggregate_within_bounds():
    _, _, ib = _ib_default()
    assert 0.3 <= ib.beta <= 2.5
    assert -0.20 <= ib.terminal_growth <= 0.05
    assert ib.fcf_base > 0
    assert ib.wacc > ib.terminal_growth + 0.01


def test_dcf_three_stage_decomposition():
    _, _, ib = _ib_default()
    d = compute_dcf_3stage(ib)
    # 10 yearly entries (5 explicit + 5 fade)
    assert len(d.yearly_fcf) == 10
    assert len(d.yearly_pv) == 10
    # explicit_pv ≈ sum of years 1-5
    assert abs(d.explicit_pv - sum(d.yearly_pv[:5])) < 0.01
    assert abs(d.fade_pv - sum(d.yearly_pv[5:10])) < 0.01
    # Terminal cap
    assert d.terminal_value > 0
    # EV = explicit + fade + tv_pv
    assert abs(d.enterprise_value - (d.explicit_pv + d.fade_pv + d.terminal_pv)) < 0.01


def test_wacc_safety_when_terminal_close():
    ib = IBInputs(
        fcf_base=2.0, growth_y1_3=0.10, growth_y4_5=0.06, terminal_growth=0.05,
        ebit_margin=0.2, reinvestment_rate=0.3, book_value=10.0,
        comparable_pe=15.0, comparable_pb=2.0, comparable_ev_ebitda=8.0,
        wacc_risk_premium=0.0, beta=0.4,
        investment_cost=10.0, exit_cost=0.0, red_flag_discount=0.0, moat=0.5,
    )
    # WACC must remain > terminal_growth + 0.01 thanks to floor
    assert ib.wacc > ib.terminal_growth + 0.01
    d = compute_dcf_3stage(ib)
    assert d.fair_value >= 0


def test_multiples_three_methods_present():
    _, _, ib = _ib_default()
    m = compute_multiples(ib)
    assert m.pe_value > 0 and m.pb_value > 0 and m.ev_ebitda_value > 0
    assert abs(m.blended - (m.pe_value + m.pb_value + m.ev_ebitda_value) / 3.0) < 0.01


def test_asset_floor_max_of_two():
    _, _, ib = _ib_default()
    a = compute_asset(ib)
    assert a.value == max(a.book_floor, a.replacement_cost)


def test_blend_weights_sum_to_one():
    _, _, ib = _ib_default()
    d = compute_dcf_3stage(ib)
    m = compute_multiples(ib)
    a = compute_asset(ib)
    b = blend_valuations(ib, d, m, a, "blue_chip")
    assert abs(sum(b.weights) - 1.0) < 1e-6
    # mid lies between low and high
    assert b.fair_low <= b.fair_mid <= b.fair_high


def test_monte_carlo_quantiles_ordered():
    _, _, ib = _ib_default()
    mc = monte_carlo(ib, "default", iters=200, seed=7)
    assert mc.p10 <= mc.p50 <= mc.p90
    assert 0.0 <= mc.prob_above_cost <= 1.0
    assert mc.iters == 200


def test_full_pipeline_smoke():
    s, ans, _ = _ib_default()
    r = run_pipeline_ib(s, ans, description="smoke", target_type=s.subject_kind, mc_iters=200)
    assert r.archetype.archetype_id in {
        "blue_chip","growth","value_trap","junk_bond","penny_stock","distressed","defensive","meme",
    }
    assert r.blended is not None and r.dcf3 is not None and r.mc is not None
    assert r.blended.fair_low <= r.blended.fair_mid <= r.blended.fair_high


def test_growth_subject_archetype():
    """High growth + low book + decent margin should lean toward growth."""
    s, ans, _ = _ib_default()
    # Push near_growth and long_growth high
    ans["near_growth"] = 7
    ans["long_growth"] = 5
    ans["red_flag_count"] = 0
    ans["effort_required"] = 4
    ans["book_assets"] = 2
    ans["volatility"] = 4
    r = run_pipeline_ib(s, ans, description="growth case", target_type=s.subject_kind, mc_iters=100)
    assert r.archetype.archetype_id in {"growth", "junk_bond", "meme", "penny_stock"}
