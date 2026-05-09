"""IB-grade valuation engine.

Pipeline: dynamic schema + answers
  → aggregate_ib_inputs(): proxy mapping → IBInputs
  → compute_dcf_3stage(): explicit (5y) + fade (5y) + Gordon terminal
  → compute_multiples(): P/E + P/B + EV/EBITDA cross-check
  → compute_asset(): liquidation / replacement floor
  → blend_valuations(): three-method weighted (50/35/15 default, archetype-tuned)
  → monte_carlo(): perturb growth + WACC + margin → P10/P50/P90

Citations:
  Gordon (1962); Damodaran (2002); Koller/Goedhart/Wessels (2020);
  Sharpe (1964) CAPM; Fama-French (1993); Markowitz (1952).
"""
from __future__ import annotations

import math
import random

from ..models import (
    DynamicSchema, DynamicField,
    IBInputs, DCF3StageResult, MultiplesResult, AssetResult,
    BlendedValuation, MonteCarloResult,
)


# ───────────────────────── 1. Aggregate proxy answers → IBInputs ─────────────────────────

def _resolve_field_value(f: DynamicField, raw) -> float:
    """Convert a raw form value to a normalized 0-1 score."""
    if f.kind == "fillin":
        # Try numeric, else count words as a proxy
        try:
            v = float(raw)
            return max(min((v - f.min) / max(f.max - f.min, 1e-9), 1.0), 0.0)
        except (TypeError, ValueError):
            words = len(str(raw or "").split())
            return max(min(words / 50.0, 1.0), 0.0)
    if f.kind == "select":
        if not f.options:
            return 0.5
        for i, opt in enumerate(f.options):
            if str(opt[0]) == str(raw):
                return 1.0 - i / max(len(f.options) - 1, 1)
        return 0.5
    # numeric kinds: likert5/likert7/number/range
    try:
        v = float(raw)
    except (TypeError, ValueError):
        v = float(f.default) if isinstance(f.default, (int, float)) else (f.min + f.max) / 2.0
    span = f.max - f.min
    if span <= 0:
        return 0.5
    return max(min((v - f.min) / span, 1.0), 0.0)


def _apply_mapping(score: float, scale: str, to_min: float, to_max: float) -> float:
    """Apply scale (linear/inverse/log) and project [0,1] → [to_min, to_max]."""
    s = max(min(score, 1.0), 0.0)
    if scale == "inverse":
        s = 1.0 - s
    elif scale == "log":
        s = math.log1p(9.0 * s) / math.log(10.0)  # log-curve flatter at high
    return to_min + s * (to_max - to_min)


# Defaults if a parameter is never bound by any field
_IB_DEFAULTS = {
    "fcf_base": 3.0,
    "revenue_growth_y1_3": 0.08,
    "revenue_growth_y4_5": 0.04,
    "terminal_growth": 0.02,
    "ebit_margin": 0.20,
    "reinvestment_rate": 0.30,
    "book_value": 10.0,
    "comparable_pe": 15.0,
    "comparable_pb": 1.8,
    "comparable_ev_ebitda": 9.0,
    "wacc_risk_premium": 0.02,
    "beta_proxy": 1.1,
    "investment_cost": 12.0,
    "exit_cost": 3.0,
    "red_flags": 0.0,
    "moat": 0.4,
}


def aggregate_ib_inputs(schema: DynamicSchema, answers: dict) -> IBInputs:
    """Aggregate answers grouped by ib_param (mean of contributors)."""
    sums: dict = {k: 0.0 for k in _IB_DEFAULTS}
    counts: dict = {k: 0 for k in _IB_DEFAULTS}

    fields = schema.all_fields if hasattr(schema, "all_fields") else schema.fields
    for f in fields:
        if not f.ib_param or f.ib_param not in sums:
            continue
        raw = answers.get(f.id, f.default)
        score = _resolve_field_value(f, raw)
        mapped = _apply_mapping(score, f.scale or "linear", f.to_min, f.to_max)
        sums[f.ib_param] += mapped
        counts[f.ib_param] += 1

    def avg(k):
        return sums[k] / counts[k] if counts[k] > 0 else _IB_DEFAULTS[k]

    fcf = max(avg("fcf_base"), 0.1)
    g13 = max(min(avg("revenue_growth_y1_3"), 0.5), -0.30)
    g45 = max(min(avg("revenue_growth_y4_5"), 0.30), -0.20)
    gt = max(min(avg("terminal_growth"), 0.05), -0.02)
    margin = max(min(avg("ebit_margin"), 0.95), 0.02)
    reinv = max(min(avg("reinvestment_rate"), 0.95), 0.0)
    bv = max(avg("book_value"), 0.5)
    pe_anchor = max(avg("comparable_pe"), 3.0)
    pb_anchor = max(avg("comparable_pb"), 0.3)
    ev_ebitda = max(avg("comparable_ev_ebitda"), 2.0)
    risk_prem = max(min(avg("wacc_risk_premium"), 0.20), 0.0)
    beta = max(min(avg("beta_proxy"), 2.5), 0.3)
    p = max(avg("investment_cost"), 0.5)
    exit_c = max(avg("exit_cost"), 0.0)
    rf_count = avg("red_flags") if counts["red_flags"] > 0 else 0.0
    rf_disc = max(min(rf_count, 0.45), 0.0)
    moat = max(min(avg("moat"), 1.0), 0.0)

    return IBInputs(
        fcf_base=fcf,
        growth_y1_3=g13,
        growth_y4_5=g45,
        terminal_growth=gt,
        ebit_margin=margin,
        reinvestment_rate=reinv,
        book_value=bv,
        comparable_pe=pe_anchor,
        comparable_pb=pb_anchor,
        comparable_ev_ebitda=ev_ebitda,
        wacc_risk_premium=risk_prem,
        beta=beta,
        investment_cost=p,
        exit_cost=exit_c,
        red_flag_discount=rf_disc,
        moat=moat,
    )


# ───────────────────────── 2. Three-stage DCF ─────────────────────────

def compute_dcf_3stage(ib: IBInputs) -> DCF3StageResult:
    """Three-stage DCF: 5y explicit (g13) + 5y fade (g13→gt) + Gordon terminal.

    Uses (1 - reinvestment_rate) of FCF as distributable; growth applied to FCF.
    """
    wacc = ib.wacc
    yearly_fcf = []
    yearly_pv = []
    fcf = ib.fcf_base

    # Stage 1: explicit 5 years at growth_y1_3
    for t in range(1, 6):
        fcf = fcf * (1 + ib.growth_y1_3)
        distributable = fcf * (1 - ib.reinvestment_rate)
        yearly_fcf.append(fcf)
        yearly_pv.append(distributable / ((1 + wacc) ** t))
    explicit_pv = sum(yearly_pv)

    # Stage 2: 5-year linear fade from growth_y1_3 → terminal_growth
    fade_pv = 0.0
    for t in range(6, 11):
        # interpolate: at t=6 use growth_y4_5, fade linearly to terminal at t=10
        alpha = (t - 5) / 5.0
        g_t = ib.growth_y4_5 * (1 - alpha) + ib.terminal_growth * alpha
        fcf = fcf * (1 + g_t)
        distributable = fcf * (1 - ib.reinvestment_rate * 0.7)  # reinvestment also fades
        pv = distributable / ((1 + wacc) ** t)
        yearly_fcf.append(fcf)
        yearly_pv.append(pv)
        fade_pv += pv

    # Stage 3: Gordon terminal at year 10
    terminal_fcf = fcf * (1 + ib.terminal_growth)
    if wacc - ib.terminal_growth > 0.001:
        tv = terminal_fcf / (wacc - ib.terminal_growth)
    else:
        tv = terminal_fcf * 25.0
    tv_pv = tv / ((1 + wacc) ** 10)

    ev = explicit_pv + fade_pv + tv_pv
    fair = ev * (1.0 - ib.red_flag_discount) - ib.exit_cost
    fair = max(fair, 0.0)
    upside = (fair - ib.investment_cost) / max(ib.investment_cost, 0.01)

    return DCF3StageResult(
        explicit_pv=explicit_pv,
        fade_pv=fade_pv,
        terminal_value=tv,
        terminal_pv=tv_pv,
        enterprise_value=ev,
        fair_value=fair,
        upside_pct=upside,
        wacc=wacc,
        yearly_fcf=tuple(yearly_fcf),
        yearly_pv=tuple(yearly_pv),
    )


# ───────────────────────── 3. Comparable multiples ─────────────────────────

def compute_multiples(ib: IBInputs) -> MultiplesResult:
    """Three multiples (P/E, P/B, EV/EBITDA), moat-tuned, then equal-weight blend."""
    # moat lifts comparable anchor up to +25%, lack of moat compresses up to -20%
    moat_lift = 1.0 + (ib.moat - 0.5) * 0.5
    pe_imp = ib.comparable_pe * moat_lift
    pb_imp = ib.comparable_pb * moat_lift
    ev_imp = ib.comparable_ev_ebitda * moat_lift

    eps = ib.fcf_base * ib.ebit_margin   # earnings = fcf × margin
    pe_value = eps * pe_imp
    pb_value = ib.book_value * pb_imp
    ebitda = ib.fcf_base * (ib.ebit_margin + ib.reinvestment_rate * 0.5)
    ev_value = ebitda * ev_imp

    pe_value *= (1.0 - ib.red_flag_discount)
    pb_value *= (1.0 - ib.red_flag_discount * 0.5)
    ev_value *= (1.0 - ib.red_flag_discount)

    blended = (pe_value + pb_value + ev_value) / 3.0
    return MultiplesResult(
        pe_implied=pe_imp, pb_implied=pb_imp, ev_ebitda_implied=ev_imp,
        pe_value=pe_value, pb_value=pb_value, ev_ebitda_value=ev_value,
        blended=blended,
    )


# ───────────────────────── 4. Asset / replacement ─────────────────────────

def compute_asset(ib: IBInputs) -> AssetResult:
    """Liquidation / replacement floor."""
    book_floor = ib.book_value * (1.0 - ib.red_flag_discount * 0.6)
    # Replacement cost: investment_cost grossed up by moat (harder to replace)
    replacement = ib.investment_cost * (1.0 + ib.moat * 1.2)
    value = max(book_floor, replacement)
    return AssetResult(book_floor=book_floor, replacement_cost=replacement, value=value)


# ───────────────────────── 5. Blended valuation ─────────────────────────

# archetype hint → weight tuple (dcf, mult, asset)
ARCHETYPE_WEIGHTS = {
    "blue_chip":   (0.55, 0.35, 0.10),
    "growth":      (0.70, 0.25, 0.05),
    "value_trap":  (0.30, 0.30, 0.40),
    "junk_bond":   (0.20, 0.30, 0.50),
    "penny_stock": (0.40, 0.40, 0.20),
    "distressed":  (0.20, 0.20, 0.60),
    "defensive":   (0.45, 0.30, 0.25),
    "meme":        (0.25, 0.55, 0.20),
    "default":     (0.50, 0.35, 0.15),
}


def blend_valuations(
    ib: IBInputs,
    dcf: DCF3StageResult,
    mult: MultiplesResult,
    asset: AssetResult,
    archetype_id: str = "default",
) -> BlendedValuation:
    w = ARCHETYPE_WEIGHTS.get(archetype_id, ARCHETYPE_WEIGHTS["default"])
    fair_mid = w[0] * dcf.fair_value + w[1] * mult.blended + w[2] * asset.value

    vals = sorted([dcf.fair_value, mult.blended, asset.value])
    spread = max(vals[2] - vals[0], fair_mid * 0.15)
    fair_low = max(fair_mid - spread * 0.55, asset.book_floor * 0.7)
    fair_high = fair_mid + spread * 0.55

    upside = (fair_mid - ib.investment_cost) / max(ib.investment_cost, 0.01)
    eps = ib.fcf_base * ib.ebit_margin
    pe_final = ib.investment_cost / max(eps, 0.01)
    pb_final = ib.investment_cost / max(ib.book_value, 0.01)

    return BlendedValuation(
        dcf_value=dcf.fair_value,
        multiples_value=mult.blended,
        asset_value=asset.value,
        weights=w,
        fair_low=fair_low,
        fair_mid=fair_mid,
        fair_high=fair_high,
        upside_pct=upside,
        pe_final=pe_final,
        pb_final=pb_final,
        eps=eps,
    )


# ───────────────────────── 6. Monte Carlo ─────────────────────────

def monte_carlo(
    ib: IBInputs,
    archetype_id: str = "default",
    iters: int = 1000,
    seed: int = 42,
) -> MonteCarloResult:
    """Perturb growth, WACC components, margin; recompute blended fair value."""
    rng = random.Random(seed)
    samples = []
    for _ in range(iters):
        ib_p = IBInputs(
            fcf_base=ib.fcf_base * rng.uniform(0.85, 1.15),
            growth_y1_3=ib.growth_y1_3 + rng.uniform(-0.04, 0.04),
            growth_y4_5=ib.growth_y4_5 + rng.uniform(-0.03, 0.03),
            terminal_growth=ib.terminal_growth + rng.uniform(-0.01, 0.01),
            ebit_margin=max(min(ib.ebit_margin + rng.uniform(-0.05, 0.05), 0.95), 0.02),
            reinvestment_rate=ib.reinvestment_rate,
            book_value=ib.book_value * rng.uniform(0.9, 1.1),
            comparable_pe=ib.comparable_pe * rng.uniform(0.85, 1.15),
            comparable_pb=ib.comparable_pb * rng.uniform(0.85, 1.15),
            comparable_ev_ebitda=ib.comparable_ev_ebitda * rng.uniform(0.85, 1.15),
            wacc_risk_premium=max(ib.wacc_risk_premium + rng.uniform(-0.01, 0.02), 0.0),
            beta=max(min(ib.beta + rng.uniform(-0.15, 0.15), 2.5), 0.3),
            investment_cost=ib.investment_cost,
            exit_cost=ib.exit_cost,
            red_flag_discount=ib.red_flag_discount,
            moat=ib.moat,
        )
        d = compute_dcf_3stage(ib_p)
        m = compute_multiples(ib_p)
        a = compute_asset(ib_p)
        b = blend_valuations(ib_p, d, m, a, archetype_id)
        samples.append(b.fair_mid)

    samples.sort()
    n = len(samples)

    def pct(p):
        idx = int(p * (n - 1))
        return samples[idx]

    mean = sum(samples) / n
    var = sum((s - mean) ** 2 for s in samples) / n
    stdev = math.sqrt(var)
    above = sum(1 for s in samples if s > ib.investment_cost) / n

    return MonteCarloResult(
        iters=iters,
        p10=pct(0.10),
        p50=pct(0.50),
        p90=pct(0.90),
        mean=mean,
        stdev=stdev,
        prob_above_cost=above,
    )
