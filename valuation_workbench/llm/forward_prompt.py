"""Self-contained prompt for generating forward-looking variables (Stage F).

Cold-start safe: every call carries full context (description + answers
summary + IB inputs). The LLM proposes 2-3 candidate forward variables, each
with explanation, suggested Δ%, and which fields to perturb.
"""
from __future__ import annotations

import json


SYSTEM_PROMPT = """你是华尔街投行的高级估值分析师, 正在为一段对象/暧昧关系做估值的最后一步: 设计前瞻变量。

【什么是前瞻变量?】
前瞻变量 = 在未来 6-12 个月内最可能改变这段关系估值的 1-3 个关键事件 (类似投行估值里的 'forward-looking key drivers')。
比如: TA 升职 / 异地变同城 / 见家长 / 我跳槽 / TA 前任回归 / 我们一起搬家 等。

【扰动幅度 (Δ%) 怎么定?】
不是用户填空, 而是你根据情境判断: 这个事件如果发生 (bull) 或者反向发生 (bear), 大概会让关键参数 (主动度/相处时间/信任等) 变化多少百分比。
保守估计: 10-20% (常见持续性影响)
中度: 25-40% (重大事件)
激进: 50%+ (颠覆性事件, 慎用)

【你的工作】
- 根据用户描述 + 全部问卷答案, 提出 2-3 个最相关的前瞻变量候选
- 每个变量给一段中文解释 (为什么这件事重要)
- 给一个推荐 Δ%
- 指定要扰动哪些 ib_param (从白名单选)
- 给一个 bull / bear 各自的具体含义说明

【硬约束】
1. 单个 JSON 对象输出, 不要 markdown 围栏, 不要前后说明。
2. 100% 中文, 不夹杂英文 (除了变量 id 用 snake_case 英文)。
3. 输出会被 Python 引擎机械读取, 严格 JSON。"""


def _user_template(description: str, schema_summary: str, answers_summary: str, ib_inputs_summary: str) -> str:
    return f"""【用户描述的估值对象】
---
{description or '(无)'}
---

【6 阶段问卷概要 (LLM 生成的子主题列表)】
{schema_summary}

【用户的全部答案 (按题目 id)】
{answers_summary}

【已计算出的 IB 内核参数 (用作背景)】
{ib_inputs_summary}

【输出 JSON shape】
{{
  "explanation_zh": "用三句话向用户解释 '什么是前瞻变量', 用对象/暧昧关系的语境举例.",
  "candidates": [
    {{
      "id": "snake_case_id",
      "name_zh": "前瞻变量名 (8 字以内, 简洁)",
      "rationale_zh": "为什么这件事在这段关系里值得作为前瞻变量 (3-5 句话, 引用用户描述里的具体细节)",
      "bull_meaning_zh": "如果这件事发生(乐观), 对关系的影响",
      "bear_meaning_zh": "如果这件事不发生或反向发生(悲观), 对关系的影响",
      "delta_pct": 0.30,
      "delta_pct_rationale_zh": "为什么选这个幅度 (1-2 句)",
      "perturb_ib_params": ["revenue_growth_y1_3", "moat"],
      "recommended": true
    }}
  ],
  "default_recommended_id": "candidates 里你最推荐用户选的那个的 id"
}}

【生成要求】
- candidates 数量: 2 个或 3 个 (太多会让用户犯选择困难)
- 每个 candidate 要紧贴用户描述里的具体细节, 不要用通用模板
- delta_pct 在 0.10 - 0.50 之间, 大多数情况 0.20 - 0.35
- perturb_ib_params 必须从这个白名单选 (1-3 个):
  fcf_base, revenue_growth_y1_3, revenue_growth_y4_5, terminal_growth, ebit_margin,
  reinvestment_rate, book_value, comparable_pe, wacc_risk_premium, beta_proxy,
  investment_cost, exit_cost, red_flags, moat
- recommended=true 标记你最推荐的那个 (有且只有 1 个)

只输出 JSON, 不要其他文本。"""


def build_forward_prompt(
    description: str,
    schema_summary: str,
    answers_summary: str,
    ib_inputs_summary: str,
) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": _user_template(description, schema_summary, answers_summary, ib_inputs_summary)},
    ]


def schema_to_summary(dyn_schema) -> str:
    """Compact human-readable summary of the schema for prompt context."""
    lines = []
    if hasattr(dyn_schema, "stages") and dyn_schema.stages:
        for st in dyn_schema.stages:
            lines.append(f"{st.id} {st.label_zh}:")
            for sub in st.sub_themes:
                fids = ", ".join(f.id for f in sub.fields)
                lines.append(f"  · {sub.name_zh} ({fids})")
    elif hasattr(dyn_schema, "fields"):
        # Flat fallback
        for f in dyn_schema.fields:
            lines.append(f"  - {f.id}: {f.label_zh[:40]}")
    return "\n".join(lines) or "(无)"


def answers_to_summary(answers: dict) -> str:
    items = []
    for k, v in answers.items():
        sv = str(v)
        if len(sv) > 80:
            sv = sv[:80] + "…"
        items.append(f"  {k}: {sv}")
    return "\n".join(items) or "(无)"


def ib_to_summary(ib) -> str:
    if ib is None:
        return "(未计算)"
    return (
        f"  fcf_base={ib.fcf_base:.2f}, growth_y1_3={ib.growth_y1_3:.3f}, "
        f"growth_y4_5={ib.growth_y4_5:.3f}, terminal_growth={ib.terminal_growth:.3f},\n"
        f"  ebit_margin={ib.ebit_margin:.2f}, reinvestment_rate={ib.reinvestment_rate:.2f}, "
        f"book_value={ib.book_value:.2f}, beta={ib.beta:.2f},\n"
        f"  wacc={ib.wacc:.3f}, comparable_pe={ib.comparable_pe:.1f}, "
        f"investment_cost={ib.investment_cost:.2f}, exit_cost={ib.exit_cost:.2f},\n"
        f"  red_flag_discount={ib.red_flag_discount:.2f}, moat={ib.moat:.2f}"
    )


# Offline fallback when no LLM is available
FALLBACK_FORWARD = {
    "explanation_zh": (
        "前瞻变量是未来 6-12 个月内最可能改变这段关系估值的关键事件 — "
        "比如 TA 升职、异地变同城、见家长等。我们用它来计算 bull / base / bear 三个场景下的估值。"
        "扰动幅度 (Δ%) 是这件事发生与否对关键参数的影响百分比。"
    ),
    "candidates": [
        {
            "id": "milestone_event",
            "name_zh": "关键里程碑事件",
            "rationale_zh": "未连接 LLM 时使用通用模板。建议你想一个能在 6-12 个月内显著改变这段关系势头的关键事件作为前瞻变量。",
            "bull_meaning_zh": "事件发生 → 关系明显升级",
            "bear_meaning_zh": "事件未发生或反向 → 关系停滞/降级",
            "delta_pct": 0.30,
            "delta_pct_rationale_zh": "30% 是中度事件的常见幅度",
            "perturb_ib_params": ["revenue_growth_y1_3", "moat"],
            "recommended": True,
        },
    ],
    "default_recommended_id": "milestone_event",
}
