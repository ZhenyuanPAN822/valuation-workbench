"""8-archetype classification based on (E, BV, P, g, beta) cluster."""
from __future__ import annotations

from ..models import ValuationCore, ArchetypeResult


# Archetype definitions: (id, label_zh, label_en, description_zh, description_en, predicates)
# Predicates are functions of (E, BV, P, pe, pb, g, beta, fair_value, upside)
ARCHETYPES = [
    {
        "id": "blue_chip",
        "label_zh": "蓝筹股",
        "label_en": "Blue Chip",
        "description_zh": "高 E, 高 BV, 低波动率, 低 PE。基本面扎实, 适合长期持有。",
        "description_en": "High earnings, high book value, low volatility, low PE. Strong fundamentals, long-term hold.",
    },
    {
        "id": "growth",
        "label_zh": "成长股",
        "label_en": "Growth Stock",
        "description_zh": "中 E, 低 BV, 高增长率, 中波动。当前账面薄但前景好。",
        "description_en": "Moderate earnings, low book, high growth, moderate volatility. Thin current book but strong outlook.",
    },
    {
        "id": "value_trap",
        "label_zh": "价值陷阱",
        "label_en": "Value Trap",
        "description_zh": "PE / PB 看起来便宜, 但 E 持续低迷, 增长为零或负。看似便宜其实是坑。",
        "description_en": "Cheap-looking PE/PB but stagnant earnings and zero/negative growth. Looks cheap but isn't.",
    },
    {
        "id": "junk_bond",
        "label_zh": "垃圾债",
        "label_en": "Junk Bond",
        "description_zh": "短期高 E, 高波动, 低 BV。短期回报但风险大。",
        "description_en": "Short-term high earnings, high volatility, low book. High return short-term but risky.",
    },
    {
        "id": "penny_stock",
        "label_zh": "细价股",
        "label_en": "Penny Stock",
        "description_zh": "全部数值都低, 但前瞻可选性高。小仓位赌不对称上行。",
        "description_en": "Low everything but high optionality. Small position for asymmetric upside.",
    },
    {
        "id": "distressed",
        "label_zh": "破产清算",
        "label_en": "Distressed Asset",
        "description_zh": "近期 E 为负, 价值持续蒸发。考虑止损或重组。",
        "description_en": "Recent earnings negative, eroding value. Consider stop-loss or restructuring.",
    },
    {
        "id": "defensive",
        "label_zh": "防御股 / 主权债",
        "label_en": "Defensive / Sovereign",
        "description_zh": "中等所有维度, 极低波动。稳定但回报有限。",
        "description_en": "Moderate everything, very low volatility. Stable but limited upside.",
    },
    {
        "id": "meme",
        "label_zh": "Meme 股",
        "label_en": "Meme Stock",
        "description_zh": "极高波动, P >> 基本面。情绪驱动, 在崩盘前撤离。",
        "description_en": "Extreme volatility, P >> fundamentals. Sentiment-driven; exit before crash.",
    },
]


def classify(core: ValuationCore, pe: float, pb: float, upside: float) -> ArchetypeResult:
    """Score each archetype and pick the best fit."""
    E = core.E
    BV = core.BV
    P = core.P
    g = core.g
    beta = core.beta

    scores = []
    # Blue Chip: high E, high BV, low beta, moderate PE
    bc = max(0, (E - 5) / 5) + max(0, (BV - 5) / 5) + max(0, (1.5 - beta) / 1.2) + max(0, (15 - pe) / 15) * 0.5
    scores.append(("blue_chip", bc))
    # Growth: moderate E, low BV, high g, moderate beta
    gr = max(0, (E - 4) / 6) * 0.7 + max(0, (5 - BV) / 5) * 0.5 + max(0, (g - 0.05) / 0.25) + max(0, (1.0 - abs(beta - 1.2)) / 1.0) * 0.3
    scores.append(("growth", gr))
    # Value Trap: low PE/PB but low E and low/neg g
    vt = max(0, (12 - pe) / 12) * 0.5 + max(0, (1.5 - pb) / 1.5) * 0.5 + max(0, (4 - E) / 4) + max(0, (0.05 - g) / 0.20)
    scores.append(("value_trap", vt))
    # Junk: high E, high beta, low BV
    jb = max(0, (E - 6) / 4) * 0.4 + max(0, (beta - 1.5) / 1.0) + max(0, (4 - BV) / 4) * 0.5
    scores.append(("junk_bond", jb))
    # Penny: low everything
    ps = max(0, (4 - E) / 4) * 0.4 + max(0, (4 - BV) / 4) * 0.4 + max(0, (4 - P) / 4) * 0.4 + max(0, (g - 0.0) / 0.25) * 0.4
    scores.append(("penny_stock", ps))
    # Distressed: low E (eroding), high P relative to E
    ds = max(0, (3 - E) / 3) + max(0, (g + 0.05) / 0.25) * 0.5 + max(0, (pe - 30) / 30) * 0.5 + max(0, (-upside) / 0.5)
    scores.append(("distressed", ds))
    # Defensive: low beta, moderate everything
    dv = max(0, (1.0 - abs(beta - 0.6)) / 1.0) + max(0, (1.0 - abs(E - 5) / 5)) * 0.5 + max(0, (1.0 - abs(BV - 5) / 5)) * 0.5
    scores.append(("defensive", dv))
    # Meme: high beta + high P + low BV
    mm = max(0, (beta - 1.7) / 0.8) + max(0, (pe - 35) / 30) + max(0, (4 - BV) / 4) * 0.5
    scores.append(("meme", mm))

    best_id, best_score = max(scores, key=lambda x: x[1])
    arch = next(a for a in ARCHETYPES if a["id"] == best_id)
    # Normalize fit_score to 0-1
    total = sum(max(s, 0.0) for _, s in scores)
    fit = best_score / max(total, 0.01)

    return ArchetypeResult(
        archetype_id=best_id,
        label_zh=arch["label_zh"],
        label_en=arch["label_en"],
        description_zh=arch["description_zh"],
        description_en=arch["description_en"],
        fit_score=min(max(fit, 0.0), 1.0),
    )
