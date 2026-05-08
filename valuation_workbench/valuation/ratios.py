"""P/E, P/B, EPS calculations + verdict labels."""
from __future__ import annotations

from ..models import ValuationCore, RatiosResult


def compute_ratios(core: ValuationCore) -> RatiosResult:
    eps = core.E   # in our metaphor, EPS ≈ E (earnings per period of attention)
    pe = core.P / max(core.E, 0.01)
    pb = core.P / max(core.BV, 0.01)

    # PE verdict (relative to "broad market" PE of ~15-20)
    if pe < 8:
        pe_zh = f"P/E = {pe:.2f} → 低估区 (低于市场)"
        pe_en = f"P/E = {pe:.2f} → undervalued vs market"
    elif pe < 18:
        pe_zh = f"P/E = {pe:.2f} → 合理估值"
        pe_en = f"P/E = {pe:.2f} → fairly valued"
    elif pe < 35:
        pe_zh = f"P/E = {pe:.2f} → 偏高 (溢价)"
        pe_en = f"P/E = {pe:.2f} → premium"
    else:
        pe_zh = f"P/E = {pe:.2f} → 极度高估 (注意 bubble 风险)"
        pe_en = f"P/E = {pe:.2f} → extreme premium (bubble risk)"

    # PB verdict (relative to ~1.5)
    if pb < 0.7:
        pb_zh = f"P/B = {pb:.2f} → 折价 (低于账面)"
        pb_en = f"P/B = {pb:.2f} → trading below book"
    elif pb < 2.0:
        pb_zh = f"P/B = {pb:.2f} → 接近账面"
        pb_en = f"P/B = {pb:.2f} → near book value"
    elif pb < 4.0:
        pb_zh = f"P/B = {pb:.2f} → 溢价"
        pb_en = f"P/B = {pb:.2f} → premium to book"
    else:
        pb_zh = f"P/B = {pb:.2f} → 极度溢价"
        pb_en = f"P/B = {pb:.2f} → extreme premium to book"

    return RatiosResult(
        pe=pe, pb=pb, eps=eps,
        pe_zh=pe_zh, pe_en=pe_en,
        pb_zh=pb_zh, pb_en=pb_en,
    )
