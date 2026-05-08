"""Investment-strategy recommendation: position, hold-period, conviction, improvements."""
from __future__ import annotations

from ..models import ValuationCore, RatiosResult, DCFResult, ArchetypeResult, StrategyResult


_POS_BY_ARCHETYPE = {
    "blue_chip":   ("LONG",  "LONG",     "BUY"),
    "growth":      ("LONG",  "MEDIUM",   "BUY"),
    "value_trap":  ("FLAT",  "TERMINATE","SELL"),
    "junk_bond":   ("LONG",  "SHORT",    "HOLD"),
    "penny_stock": ("LONG",  "LONG",     "HOLD"),
    "distressed":  ("SHORT", "TERMINATE","STRONG_SELL"),
    "defensive":   ("LONG",  "LONG",     "HOLD"),
    "meme":        ("HEDGE", "SHORT",    "SELL"),
}

_RATIONALE_ZH = {
    "blue_chip":   "高基本面 + 低波动 = 做多, 长期持有, 买入。这是教科书 buy-and-hold 标的。",
    "growth":      "中等当前 E 但增长强 = 做多, 中期持有, 买入并跟踪 g 假设是否兑现。",
    "value_trap":  "PE / PB 看似便宜但 E 没有提升迹象 = 不要被低估值诱惑, 终止仓位, 转向更好标的。",
    "junk_bond":   "高短期 E 但波动剧烈 = 可以做多但严控止损, 短期持有, 不加仓。",
    "penny_stock": "基本面薄但有不对称上行选项 = 小仓位做多, 长期持有, 等催化剂。",
    "distressed":  "近期 E 萎缩, 价值蒸发中 = 做空或快速止损出局, 不再投入。",
    "defensive":   "稳定但平庸 = 做多但只作为 portfolio 中的稳定器, 不期望高回报。",
    "meme":        "P 已远超基本面 = 用 hedge 锁定收益或减仓, 短期内寻找退出, 警惕 crash。",
}
_RATIONALE_EN = {
    "blue_chip":   "Strong fundamentals + low vol = Long, long-term hold, Buy. Textbook buy-and-hold.",
    "growth":      "Moderate current E but strong growth = Long, medium-term, Buy; monitor g realization.",
    "value_trap":  "Cheap PE/PB but stagnant E = ignore the discount, terminate, rotate to better.",
    "junk_bond":   "High short-term E but volatile = Long with tight stop, short hold, no add.",
    "penny_stock": "Thin fundamentals + asymmetric upside = small Long, long hold, await catalyst.",
    "distressed":  "Eroding earnings = Short or fast exit, no further capital.",
    "defensive":   "Stable but mediocre = Long as portfolio stabilizer, low expected return.",
    "meme":        "P >> fundamentals = Hedge or trim, short-term exit hunt, watch for crash.",
}


def _improvements(target_type: str, archetype_id: str, ratios: RatiosResult, dcf: DCFResult) -> tuple:
    """Return 3-5 actionable improvement suggestions in zh."""
    base = []
    if archetype_id == "value_trap":
        base = [
            "停止增加投入 — 不要被低 PE 误导。",
            "诚实评估: TA 的 E 在过去 6 个月真的有提升迹象吗?如果没有, 这就是 trap。",
            "把节省下来的时间和情感分配到 alt option (备选标的)。",
        ]
    elif archetype_id == "blue_chip":
        base = [
            "继续投入,但避免 over-paying — 不要在估值过高时追加。",
            "巩固已有基础(BV)而非追逐短期 E 提升。",
            "建议 long-term 关系节点(见家长/同居等)推进。",
        ]
    elif archetype_id == "growth":
        base = [
            "锁定增长率假设(g)的关键里程碑 — 比如未来 3 个月 TA 的具体行为。",
            "如果 g 兑现,考虑加仓; 如果 g 落空, 重新评估为 junk 或 trap。",
            "保持开放的备选(alt options),降低 single-bet 风险。",
        ]
    elif archetype_id == "junk_bond":
        base = [
            "设定明确止损线 — 当 E 下跌 30% 时退出。",
            "不要重仓 — junk 应只占你 'portfolio' 一小部分。",
            "享受短期 E 但不要把它当 long 标的。",
        ]
    elif archetype_id == "penny_stock":
        base = [
            "保持小仓位 — 不要 over-commit 到一个 thin fundamentals 的标的。",
            "明确催化剂(catalyst): 什么事件会让这个标的从 penny 升级到 growth?",
            "如果 12 个月没有催化剂, 退出。",
        ]
    elif archetype_id == "distressed":
        base = [
            "立即停止追加投入。",
            "评估退出成本(exit cost), 选择最低成本路径离场。",
            "做事后复盘: 当初哪些信号被你忽视了?",
        ]
    elif archetype_id == "defensive":
        base = [
            "接受低回报 — 不要期待这个标的产生 alpha。",
            "用作 portfolio 稳定器, 不要把它当主仓。",
            "保持 BV 不要折损,无需大幅增仓。",
        ]
    elif archetype_id == "meme":
        base = [
            "用 hedge 锁定已有收益(比如建立 backup 关系/选项)。",
            "P 已透支基本面 — 任何利空都会引发 crash。",
            "提前规划退出路径,不要等到崩盘再走。",
        ]
    else:
        base = [
            "审视当前 E 的可持续性。",
            "评估 g 假设是否过度乐观。",
            "保持对 alt options 的关注。",
        ]
    if dcf.upside_pct > 0.5:
        base.append(f"DCF 显示上行空间 {dcf.upside_pct*100:.0f}%, 可适度加仓。")
    elif dcf.upside_pct < -0.3:
        base.append(f"DCF 显示下行 {-dcf.upside_pct*100:.0f}%, 减仓优先。")
    return tuple(base[:5])


def _improvements_en(archetype_id: str, dcf: DCFResult) -> tuple:
    base = {
        "blue_chip": [
            "Continue investing but avoid over-paying — don't add at extreme valuations.",
            "Strengthen fundamentals (BV) rather than chase short-term E growth.",
            "Push for long-term commitment milestones.",
        ],
        "growth": [
            "Lock in concrete g milestones — what behaviors confirm growth in 3 months?",
            "Add if g realizes; reclassify if g falters.",
            "Keep alt options to limit single-bet risk.",
        ],
        "value_trap": [
            "Stop adding. The cheap PE is a trap.",
            "Honestly: has E meaningfully improved in 6 months?",
            "Reallocate to a better target.",
        ],
        "junk_bond": [
            "Set explicit stop-loss at -30% E.",
            "Keep position size small.",
            "Enjoy short-term E but don't treat as long-term.",
        ],
        "penny_stock": [
            "Small position only.",
            "Define a catalyst — what would upgrade this from penny to growth?",
            "Exit if no catalyst in 12 months.",
        ],
        "distressed": [
            "Stop adding immediately.",
            "Evaluate exit cost; pick lowest-cost path out.",
            "Post-mortem: what signals were ignored?",
        ],
        "defensive": [
            "Accept low return — no alpha expected here.",
            "Stabilizer only, not core position.",
            "Maintain BV; no large adds needed.",
        ],
        "meme": [
            "Hedge existing gains (build backups).",
            "P >> fundamentals; any bad news triggers crash.",
            "Plan exit early; don't wait for crash.",
        ],
    }
    out = list(base.get(archetype_id, ["Review E sustainability.", "Re-examine g assumption.", "Track alt options."]))
    if dcf.upside_pct > 0.5:
        out.append(f"DCF upside {dcf.upside_pct*100:.0f}%; can scale up modestly.")
    elif dcf.upside_pct < -0.3:
        out.append(f"DCF downside {-dcf.upside_pct*100:.0f}%; trim first.")
    return tuple(out[:5])


def recommend(core: ValuationCore, ratios: RatiosResult, dcf: DCFResult, archetype: ArchetypeResult, target_type: str = "person") -> StrategyResult:
    pos, hold, conv = _POS_BY_ARCHETYPE.get(archetype.archetype_id, ("FLAT", "MEDIUM", "HOLD"))
    rationale_zh = _RATIONALE_ZH.get(archetype.archetype_id, "")
    rationale_en = _RATIONALE_EN.get(archetype.archetype_id, "")
    imp_zh = _improvements(target_type, archetype.archetype_id, ratios, dcf)
    imp_en = _improvements_en(archetype.archetype_id, dcf)

    return StrategyResult(
        position=pos,
        hold_period=hold,
        conviction=conv,
        rationale_zh=rationale_zh,
        rationale_en=rationale_en,
        improvements_zh=imp_zh,
        improvements_en=imp_en,
    )
