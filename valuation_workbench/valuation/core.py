"""Aggregate user answers into core valuation primitives (E, BV, P, g, beta, WACC).

E  — earnings per period (positive value flow)
BV — book value (revealed assets)
P  — price (your investment cost)
g  — growth rate (annualized, decimal)
beta — volatility coefficient (CAPM-style)
WACC — weighted average cost of capital (decimal)
"""
from __future__ import annotations

from ..models import Answers, Schema, ValuationCore


# Risk-free rate proxy (12% — reflects opportunity cost)
RISK_FREE = 0.12
MARKET_PREMIUM = 0.06  # equity risk premium


def _resolve_value(field, raw):
    """Convert a raw answer (slider int, radio string, multi-list) to a numeric score."""
    if field.kind == "slider" or field.kind == "number":
        try:
            return float(raw)
        except (TypeError, ValueError):
            return float(field.default)
    if field.kind == "radio":
        # Map radio choices to a 0-1 score by their position in options
        if not field.options:
            return 0.0
        for i, opt in enumerate(field.options):
            if opt[0] == raw:
                # Map first option to high score, last to low
                return 10.0 * (1.0 - i / max(len(field.options) - 1, 1))
        return 5.0
    if field.kind == "multi":
        if isinstance(raw, list):
            # Each selected option contributes 10/len(options)
            return 10.0 * (len(raw) / max(len(field.options), 1))
        return 0.0
    return 0.0


def compute_core(schema: Schema, answers: Answers) -> ValuationCore:
    """Aggregate answers into ValuationCore."""
    e_sum = 0.0
    bv_sum = 0.0
    p_sum = 0.0
    g_sum = 0.0
    vol_sum = 0.0
    e_w = 0.0
    bv_w = 0.0
    p_w = 0.0
    g_w = 0.0
    vol_w = 0.0

    for field in schema.fields:
        raw = answers.values.get(field.id, field.default)
        v = _resolve_value(field, raw)
        if field.weight_e:
            e_sum += v * field.weight_e
            e_w += abs(field.weight_e)
        if field.weight_bv:
            bv_sum += v * field.weight_bv
            bv_w += abs(field.weight_bv)
        if field.weight_p:
            p_sum += v * field.weight_p
            p_w += abs(field.weight_p)
        if field.weight_g:
            g_sum += v * field.weight_g
            g_w += abs(field.weight_g)
        if field.weight_vol:
            vol_sum += v * field.weight_vol
            vol_w += abs(field.weight_vol)

    # Normalize sums to interpretable units
    E = max(e_sum / max(e_w, 1.0), 0.1)        # earnings per period (≥0.1)
    BV = max(bv_sum / max(bv_w, 1.0), 0.1)
    # Scale P to market-comparable range (typical PE 5-30 means P ≈ 5-30 × E)
    # Our raw p_sum is on a 0-10 scale; scaling factor of ~3 brings PE into reasonable range
    P_raw = max(p_sum / max(p_w, 1.0), 0.1)
    P = P_raw * 3.0    # so a max-investment input (10 raw) ⇒ P ≈ 30 ⇒ PE ≈ 30/5 ≈ 6 for moderate E
    # g is annualized growth (decimal); cap to [-0.5, 0.5]
    g_score = g_sum / max(g_w, 1.0) if g_w > 0 else 5.0
    g = max(min((g_score - 5.0) * 0.04, 0.30), -0.20)  # ±20-30%
    # beta in [0.3, 2.5]
    vol_score = vol_sum / max(vol_w, 1.0) if vol_w > 0 else 5.0
    beta = max(min(0.3 + (vol_score / 10.0) * 2.0, 2.5), 0.3)
    # CAPM-style WACC
    wacc = RISK_FREE + beta * MARKET_PREMIUM
    # Safety: WACC > g
    if wacc <= g + 0.01:
        wacc = g + 0.02

    return ValuationCore(E=E, BV=BV, P=P, g=g, beta=beta, wacc=wacc)
