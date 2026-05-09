"""Self-contained prompt for generating the IB-grade narrative report (Stage D).

Cold-start safe: full context every call (description + answers + IB inputs +
all valuation results). LLM returns ONLY structured fields — never raw HTML.
The frontend wraps the fields in static HTML templates.
"""
from __future__ import annotations


SYSTEM_PROMPT = """你是华尔街顶级投行的资深 MD (Managing Director), 正在给客户写一份正式的估值备忘录 (valuation memo) 的叙事部分。

【产品语境】
本产品给"对象 / 暧昧对象"做投行级估值。本地引擎已经计算出全部数值 (DCF / 倍数 / 资产 / blended fair value / 蒙卡 P10/P50/P90 / archetype 分类)。
你的工作是把这些冷冰冰的数字翻译成 "Investment Memo" 风格的叙事段落。

【硬约束】
1. 单个 JSON 对象输出, 不要 markdown 围栏 (不要 ```json), 不要前后说明文字。
2. 你只输出结构化字段 (thesis_zh / risks[] 等), 不要返回 HTML 或 markdown — 前端会用静态模板渲染。
3. 100% 中文, 不混英文。
4. 用投行 MD 的语气: 严谨, 数据驱动, 引用具体数值, 不卖鸡汤。
5. 必须引用本地引擎给的具体数值 (公允价值带, P/E, 上行空间百分比等), 不要泛泛而谈。
6. 不要使用 WACC / DCF / EBITDA 等术语 — 用"折现价值 / 内在估值 / 经营利润率"等中文替代。
7. 输出会被 Python 引擎机械读取, 严格 JSON 是硬性要求。"""


def _user_template(
    description: str,
    answers_summary: str,
    ib_summary: str,
    valuation_summary: str,
    archetype_summary: str,
    forward_summary: str,
) -> str:
    return f"""【用户描述的估值对象】
---
{description or '(无)'}
---

【用户答案概要】
{answers_summary}

【本地引擎计算的内核参数】
{ib_summary}

【三法估值结果 + 综合公允价值带】
{valuation_summary}

【自动分类的 archetype】
{archetype_summary}

【前瞻变量与三场景】
{forward_summary}

【输出 JSON shape (严格按键名)】
{{
  "thesis_zh": "投资论点: 3 段, 每段 80-120 字. 第一段下结论(买/持/卖), 第二段说为什么(引用具体数字), 第三段说哪个变量是关键摆动因子.",
  "bull_narrative_zh": "Bull 场景叙事: 3-4 句, 描述如果一切如愿这段关系会变成什么样, 引用 P90 公允价值数字.",
  "base_narrative_zh": "Base 场景叙事: 3-4 句, 描述最可能的中性走向, 引用 P50 数字.",
  "bear_narrative_zh": "Bear 场景叙事: 3-4 句, 描述如果出问题会怎样, 引用 P10 数字.",
  "top_risks": [
    {{
      "title_zh": "风险标题(8 字内)",
      "trigger_zh": "什么事件会触发这个风险 (1 句)",
      "consequence_zh": "如果触发后果是 (1-2 句, 量化影响)",
      "early_signal_zh": "早期信号是什么 (1 句, 用户能观察到)"
    }}
  ],
  "actions_this_week_zh": ["本周可立刻做的 2-3 个具体动作"],
  "actions_this_month_zh": ["本月该做的 2-3 个具体动作"],
  "actions_quarter_zh": ["未来 1-3 个月的 2-3 个动作"],
  "exit_strategy_zh": "退出策略: 4-6 句, 说明什么条件下应止损, 怎么优雅退出, 退出后多久恢复.",
  "key_assumptions_zh": [
    "本次估值的 3-5 个关键假设, 每个 1 句, 引用具体数值. 比如 '假设 TA 的主动度年化增长 12%, 来自你近期答题的 5 分(7 分制)'."
  ],
  "comparable_narrative_zh": "横向对照叙事: 3-4 句, 串起用户在 B4 阶段提到的同龄人/前任/类似案例对照.",
  "verdict_one_liner_zh": "一句话总结: 不超过 30 字, 给用户一个能贴在墙上的 takeaway."
}}

【生成要求】
- top_risks 数量: 3 个 (按严重度从高到低排)
- 所有 actions 列表: 2-3 项即可, 每项必须是动词开头的可执行动作 (不是反思类)
- 引用具体数值时用中文格式: "P50 公允价值 28.06" 而不是 "P50 fair value 28.06"
- thesis_zh 第一段必须明确给出 BUY / HOLD / SELL 之一 (用中文: 加仓 / 持有 / 减仓)

只输出 JSON, 不要其他文本。"""


def build_narrative_prompt(
    description: str,
    answers_summary: str,
    ib_summary: str,
    valuation_summary: str,
    archetype_summary: str,
    forward_summary: str,
) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": _user_template(
            description, answers_summary, ib_summary, valuation_summary, archetype_summary, forward_summary,
        )},
    ]


def valuation_to_summary(report) -> str:
    """Build a numerical summary string for prompt input."""
    bl = report.blended
    mc = report.mc
    if bl is None:
        return "(估值未计算)"
    return (
        f"  三法分别: DCF 三阶段={bl.dcf_value:.2f} (权重 {bl.weights[0]*100:.0f}%), "
        f"可比公司倍数={bl.multiples_value:.2f} (权重 {bl.weights[1]*100:.0f}%), "
        f"资产法={bl.asset_value:.2f} (权重 {bl.weights[2]*100:.0f}%)\n"
        f"  综合公允价值带: P10={bl.fair_low:.2f} / P50={bl.fair_mid:.2f} / P90={bl.fair_high:.2f}\n"
        f"  P/E={bl.pe_final:.2f}, P/B={bl.pb_final:.2f}, EPS={bl.eps:.2f}\n"
        f"  投资成本={report.ib_inputs.investment_cost:.2f}, 上行空间={bl.upside_pct*100:+.1f}%\n"
        f"  蒙卡 P10/P50/P90={mc.p10:.2f}/{mc.p50:.2f}/{mc.p90:.2f}, "
        f"P(公允>成本)={mc.prob_above_cost*100:.1f}%, 标准差={mc.stdev:.2f}"
    )


def archetype_to_summary(report) -> str:
    a = report.archetype
    return f"  {a.archetype_id} ({a.label_zh}, 拟合度 {a.fit_score*100:.0f}%): {a.description_zh}"


def forward_to_summary(report) -> str:
    if not report.scenarios:
        return "(无)"
    lines = []
    for name, sc in report.scenarios.items():
        if isinstance(sc, dict):
            lines.append(
                f"  {name}: 公允={sc.get('fair_mid', 0):.2f}, "
                f"上行={sc.get('upside_pct', 0)*100:+.1f}%, g={sc.get('g', 0)*100:+.1f}%"
            )
    fname = report.forward_var_name or "(自动)"
    return f"  前瞻变量: {fname}\n" + "\n".join(lines)


# Offline fallback narrative when LLM is unavailable
def fallback_narrative(report) -> dict:
    bl = report.blended
    mc = report.mc
    arch = report.archetype
    upside = bl.upside_pct * 100 if bl else 0
    return {
        "thesis_zh": (
            f"基于本地引擎计算, 当前 archetype 为 {arch.label_zh} (拟合度 {arch.fit_score*100:.0f}%), "
            f"综合公允价值 P50 = {bl.fair_mid:.2f}, 上行空间 {upside:+.1f}%。"
            "未连接 LLM, 这里只给出本地数值快照, 详细叙事请连接 LLM 后重新生成。\n\n"
            "建议你结合 P10/P50/P90 公允价值带和蒙卡概率, 以及自己的具体感受, 做出自己的判断。"
        ),
        "bull_narrative_zh": f"乐观情景下公允价值约 {bl.fair_high:.2f}, 上行可观。",
        "base_narrative_zh": f"中性情景下公允价值约 {bl.fair_mid:.2f}, 接近当前投入成本。",
        "bear_narrative_zh": f"悲观情景下公允价值约 {bl.fair_low:.2f}, 注意下行风险。",
        "top_risks": [
            {"title_zh": "波动率过高", "trigger_zh": "状态/态度起伏剧烈",
             "consequence_zh": "估值不稳定, 难以做长期承诺", "early_signal_zh": "周间情绪反转"},
            {"title_zh": "成长率不及预期", "trigger_zh": "近期主动度下滑",
             "consequence_zh": "DCF 值快速折损", "early_signal_zh": "回复速度变慢"},
            {"title_zh": "退出成本累积", "trigger_zh": "投入持续上升而无明确进展",
             "consequence_zh": "止损越来越难", "early_signal_zh": "你开始合理化对方的冷淡"},
        ],
        "actions_this_week_zh": ["列出本周 2-3 个最关键的观察指标", "和 1 个朋友过一遍现状"],
        "actions_this_month_zh": ["设计 1 次能验证关键假设的互动", "记录每周一次客观打分"],
        "actions_quarter_zh": ["设定明确的 3 个月 milestone", "如果 milestone 没达到, 开始降低投入"],
        "exit_strategy_zh": "如果 3 个月后核心数值持续下行 30%+, 应进入降仓模式; 优雅退出的核心是不再主动加仓, 让对方的主动度成为唯一驱动。",
        "key_assumptions_zh": [
            f"假设近期成长率为 {report.ib_inputs.growth_y1_3*100:+.1f}%",
            f"假设特异风险溢价为 {report.ib_inputs.wacc_risk_premium*100:.1f}%",
            f"假设 moat 为 {report.ib_inputs.moat:.2f}",
        ],
        "comparable_narrative_zh": "未连接 LLM, 横向对照需手动思考。",
        "verdict_one_liner_zh": (
            f"{arch.label_zh}, 公允约 {bl.fair_mid:.0f}, "
            + ("加仓" if upside > 30 else ("持有" if upside > -10 else "减仓"))
        ),
    }
