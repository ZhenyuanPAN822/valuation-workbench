"""Markdown / JSON export of ForensicsReport."""
from __future__ import annotations

import json

from .models import ForensicsReport


_DISCLAIMER_ZH = "本估值基于 IB 方法的隐喻映射, 半严肃 meme 工具, 仅作参考, 非财务建议, 非心理咨询。"
_DISCLAIMER_EN = "Half-serious tool using IB metaphors. Not financial or relationship advice."


def to_markdown(r: ForensicsReport, lang: str = "zh") -> str:
    if lang == "zh":
        lines = ["# 估值报告 / Tear Sheet", ""]
        lines.append(f"- 估值对象: **{r.target_type}**")
        lines.append(f"- 前瞻变量: {r.forward_var_name or '(默认)'}")
        lines.append("")
        lines.append("## 核心指标")
        lines.append(f"- E (每期收益): {r.core.E:.2f}")
        lines.append(f"- BV (账面价值): {r.core.BV:.2f}")
        lines.append(f"- P (你的投入): {r.core.P:.2f}")
        lines.append(f"- g (增长率): {r.core.g*100:.1f}%")
        lines.append(f"- β (波动率): {r.core.beta:.2f}")
        lines.append(f"- WACC (机会成本): {r.core.wacc*100:.1f}%")
        lines.append("")
        lines.append("## 估值倍数")
        lines.append(f"- EPS: {r.ratios.eps:.2f}")
        lines.append(f"- {r.ratios.pe_zh}")
        lines.append(f"- {r.ratios.pb_zh}")
        lines.append("")
        lines.append("## DCF 估值")
        lines.append(f"- 5 年 PV: {r.dcf.five_year_pv:.2f}")
        lines.append(f"- 终值 (Gordon): {r.dcf.terminal_value:.2f}")
        lines.append(f"- 终值贴现: {r.dcf.terminal_pv:.2f}")
        lines.append(f"- **公允价值: {r.dcf.fair_value:.2f}**")
        lines.append(f"- 上行/下行: **{r.dcf.upside_pct*100:+.1f}%**")
        lines.append("")
        lines.append("## 敏感性分析 (g × WACC)")
        lines.append("")
        header = "| g \\ WACC | " + " | ".join(f"{w*100:.1f}%" for w in r.sensitivity.wacc_grid) + " |"
        lines.append(header)
        lines.append("|" + "---|" * (len(r.sensitivity.wacc_grid) + 1))
        for i, g in enumerate(r.sensitivity.g_grid):
            row = f"| {g*100:+.1f}% | " + " | ".join(f"{v:.1f}" for v in r.sensitivity.table[i]) + " |"
            lines.append(row)
        lines.append("")
        lines.append("## 三场景 (Bear / Base / Bull)")
        for name in ("bear", "base", "bull"):
            sc = r.scenarios.get(name, {})
            if isinstance(sc, dict) and "E" in sc:
                lines.append(f"- {name}: E={sc['E']:.2f}, g={sc.get('g', 0)*100:.1f}%, WACC={sc.get('wacc', 0)*100:.1f}%")
        lines.append("")
        lines.append(f"## 投资类型 / 原型")
        lines.append(f"**{r.archetype.label_zh}** (拟合度 {r.archetype.fit_score*100:.0f}%)")
        lines.append("")
        lines.append(r.archetype.description_zh)
        lines.append("")
        lines.append("## 投资策略")
        lines.append(f"- 仓位: **{r.strategy.position}**")
        lines.append(f"- 持有期: **{r.strategy.hold_period}**")
        lines.append(f"- 信心: **{r.strategy.conviction}**")
        lines.append("")
        lines.append(r.strategy.rationale_zh)
        lines.append("")
        lines.append("## 改进建议")
        for i, imp in enumerate(r.strategy.improvements_zh, 1):
            lines.append(f"{i}. {imp}")
        lines.append("")
        if r.warnings:
            lines.append("## 警告")
            for w in r.warnings:
                lines.append(f"- {w}")
            lines.append("")
        lines.append("## 文献引用")
        for c in r.citations:
            lines.append(f"- {c}")
        lines.append("")
        lines.append("---")
        lines.append(_DISCLAIMER_ZH)
    else:
        lines = ["# Valuation Tear Sheet", ""]
        lines.append(f"- Target: **{r.target_type}**")
        lines.append(f"- Forward variable: {r.forward_var_name or '(default)'}")
        lines.append("")
        lines.append("## Core Metrics")
        lines.append(f"- E (earnings per period): {r.core.E:.2f}")
        lines.append(f"- BV (book value): {r.core.BV:.2f}")
        lines.append(f"- P (your investment): {r.core.P:.2f}")
        lines.append(f"- g (growth): {r.core.g*100:.1f}%")
        lines.append(f"- β (vol): {r.core.beta:.2f}")
        lines.append(f"- WACC: {r.core.wacc*100:.1f}%")
        lines.append("")
        lines.append("## Multiples")
        lines.append(f"- EPS: {r.ratios.eps:.2f}")
        lines.append(f"- {r.ratios.pe_en}")
        lines.append(f"- {r.ratios.pb_en}")
        lines.append("")
        lines.append("## DCF")
        lines.append(f"- 5-yr PV: {r.dcf.five_year_pv:.2f}")
        lines.append(f"- Terminal value: {r.dcf.terminal_value:.2f}")
        lines.append(f"- Terminal PV: {r.dcf.terminal_pv:.2f}")
        lines.append(f"- **Fair value: {r.dcf.fair_value:.2f}**")
        lines.append(f"- Upside/downside: **{r.dcf.upside_pct*100:+.1f}%**")
        lines.append("")
        lines.append("## Archetype")
        lines.append(f"**{r.archetype.label_en}** (fit {r.archetype.fit_score*100:.0f}%)")
        lines.append("")
        lines.append(r.archetype.description_en)
        lines.append("")
        lines.append("## Strategy")
        lines.append(f"- Position: **{r.strategy.position}**")
        lines.append(f"- Hold period: **{r.strategy.hold_period}**")
        lines.append(f"- Conviction: **{r.strategy.conviction}**")
        lines.append("")
        lines.append(r.strategy.rationale_en)
        lines.append("")
        lines.append("## Improvements")
        for i, imp in enumerate(r.strategy.improvements_en, 1):
            lines.append(f"{i}. {imp}")
        lines.append("")
        lines.append("## Citations")
        for c in r.citations:
            lines.append(f"- {c}")
        lines.append("")
        lines.append("---")
        lines.append(_DISCLAIMER_EN)
    return "\n".join(lines)


def to_json(r: ForensicsReport) -> str:
    return json.dumps(r.to_dict(), indent=2, ensure_ascii=False, default=str)
