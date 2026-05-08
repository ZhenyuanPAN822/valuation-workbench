"""Discounted Cash Flow + Gordon terminal value + sensitivity table.

Citations:
  Gordon, M. J. (1962). The Investment, Financing, and Valuation of the Corporation.
  Damodaran, A. (2002). Investment Valuation.
"""
from __future__ import annotations

from ..models import ValuationCore, DCFResult, SensitivityResult


def compute_dcf(core: ValuationCore, years: int = 5) -> DCFResult:
    """5-year DCF + Gordon terminal value at year `years`."""
    E = core.E
    g = core.g
    wacc = core.wacc
    P = core.P

    # Year-by-year discounted earnings
    pv_sum = 0.0
    e_t = E
    for t in range(1, years + 1):
        e_t = E * ((1 + g) ** t)
        pv_sum += e_t / ((1 + wacc) ** t)

    # Gordon terminal value at year `years` using e_t and stable g
    if wacc <= g + 0.001:
        # Safety guard (M1)
        tv = e_t * (1 + g) * 20  # cap; in practice this should not happen due to core safety
    else:
        tv = e_t * (1 + g) / (wacc - g)
    tv_pv = tv / ((1 + wacc) ** years)

    fair_value = pv_sum + tv_pv
    upside_pct = (fair_value - P) / max(P, 0.01)

    return DCFResult(
        five_year_pv=pv_sum,
        terminal_value=tv,
        terminal_pv=tv_pv,
        fair_value=fair_value,
        upside_pct=upside_pct,
        wacc=wacc,
        g=g,
    )


def sensitivity_table(core: ValuationCore, years: int = 5) -> SensitivityResult:
    """Generate 5×5 sensitivity table varying g and WACC ±30%."""
    base_g = core.g
    base_wacc = core.wacc
    # 5 g-levels (rows): -30%, -15%, base, +15%, +30%
    g_factors = (-0.30, -0.15, 0.0, 0.15, 0.30)
    g_grid = tuple(round(base_g + abs(base_g) * f if base_g != 0 else 0.05 * (i - 2), 4)
                   for i, f in enumerate(g_factors))
    # 5 wacc-levels (cols): -30% .. +30%
    wacc_factors = (-0.30, -0.15, 0.0, 0.15, 0.30)
    wacc_grid = tuple(round(max(base_wacc * (1 + f), 0.02), 4) for f in wacc_factors)

    table = []
    for g in g_grid:
        row = []
        for wacc in wacc_grid:
            if wacc <= g + 0.001:
                wacc_eff = g + 0.02
            else:
                wacc_eff = wacc
            # compute DCF with this (g, wacc)
            E = core.E
            pv_sum = 0.0
            e_t = E
            for t in range(1, years + 1):
                e_t = E * ((1 + g) ** t)
                pv_sum += e_t / ((1 + wacc_eff) ** t)
            tv = e_t * (1 + g) / (wacc_eff - g) if wacc_eff > g + 0.001 else e_t * (1 + g) * 20
            tv_pv = tv / ((1 + wacc_eff) ** years)
            row.append(round(pv_sum + tv_pv, 2))
        table.append(tuple(row))

    return SensitivityResult(
        g_grid=g_grid,
        wacc_grid=wacc_grid,
        table=tuple(table),
    )
