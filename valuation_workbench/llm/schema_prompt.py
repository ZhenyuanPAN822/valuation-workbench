"""Self-contained prompt for generating a 6-stage personalized valuation schema.

Each call is treated as cold-start. ALL context (product spec, IB workflow,
parameter whitelist, output JSON contract, anchor requirements) is restated
every call — many gateway APIs do not preserve conversation history.
"""
from __future__ import annotations


# IB parameters the deterministic engine consumes. The LLM picks one per field.
IB_PARAMS = {
    "fcf_base":            "对象/暧昧对象基线价值流(年化): 你和 TA 相处时获得的正面情绪/陪伴/支持/性吸引力等综合价值的当期数值",
    "revenue_growth_y1_3": "近期(1-3 个月)关系成长率(decimal)。捕捉势头",
    "revenue_growth_y4_5": "中期(3-12 个月)成长率(decimal)。捕捉持续性",
    "terminal_growth":     "长期稳态成长率(decimal, 必须 < WACC)。捕捉关系是否能进入稳定阶段",
    "ebit_margin":         "信号清晰度/正面体验占比 (0-1)。每次互动里, 真正提供价值的部分比例",
    "reinvestment_rate":   "再投入率 (0-1)。维持现状你必须不断付出的精力比例",
    "book_value":          "硬资产 (TA 已经累积的稀缺资产: 性格/经历/技能/共同回忆等综合)",
    "comparable_pe":       "可比公司 P/E 锚点。同龄/同 type 人的市场倍数",
    "comparable_pb":       "可比公司 P/B 锚点",
    "comparable_ev_ebitda":"EV/EBITDA 锚点",
    "wacc_risk_premium":   "特异风险溢价(decimal)。不确定性越高越大",
    "beta_proxy":          "波动率/敏感度 (0.3-2.5)。情绪/态度起伏越大越高",
    "investment_cost":     "你的投入成本: 时间+情绪+金钱合计",
    "exit_cost":           "退出成本/锁定程度",
    "red_flags":           "红旗事件计数(0-N), 每个加折扣",
    "moat":                "护城河(0-1): TA 在你心里有多 unique / 不可替代",
}


# 6 canonical IB stages, each with hint of its purpose. Static — these always exist.
SIX_STAGES = [
    ("B1", "她/他是谁 · 基本盘", "对应 IB 的'业务理解 + 历史财务'。理清 TA 是什么样的人、过往关系/生活轨迹、剔除节日/出差等一次性事件后的日常基线。"),
    ("B2", "走向哪里 · 趋势与预测", "对应 IB 的'预测建模'。分析最近 3 个月趋势、亲密层级走向、未来 12 个月预期。"),
    ("B3", "相处含金量 · 内在估值 (DCF 视角)", "对应 IB 的'DCF 内在估值'。每次相处的情绪能量、稳定性、价值流稳定度。"),
    ("B4", "横向对照 · 市场与先例", "对应 IB 的'可比公司 + 先例交易'。和同龄人、你前任、身边类似 type 的人比较, 对照成功/失败先例。"),
    ("B5", "你的成本与退路 · LBO floor", "对应 IB 的'LBO 估值/清算底价'。你已投入多少、推掉了什么、退出代价、心理仓位。"),
    ("B6", "压力情景与边界", "对应 IB 的'敏感性 + 情景分析'。最坏情况下的承受能力、关键拐点、判断会变的边界条件。"),
]


SYSTEM_PROMPT = """你是华尔街投行的估值结构师 (valuation structurer)。

【产品语境】
本产品是一个给"对象 / 暧昧对象"做投行级别估值的工具。用户描述自己的对象或暧昧对象的情况, 你根据描述生成一份个性化的 6 阶段问卷, 每阶段问卷由你决定要问哪些子主题、哪些题目。

【6 个阶段固定 (静态骨架)】
B1 她/他是谁 · 基本盘 (对应业务理解+历史财务)
B2 走向哪里 · 趋势与预测 (对应预测建模)
B3 相处含金量 · 内在估值 (DCF) (对应 DCF)
B4 横向对照 · 市场与先例 (对应可比公司+先例交易)
B5 你的成本与退路 · LBO floor (对应 LBO/清算)
B6 压力情景与边界 (对应敏感性分析)

【你的工作 (动态生成)】
- 在每个 stage 内部, 根据用户描述的具体情况, 决定 2-3 个子主题 (sub_themes)
- 每个子主题写 4-6 道题目 (整个 schema 加起来 30-50 题)
- 每道题必须个性化贴合用户描述, 不要使用通用模板

【硬约束】
1. 输出必须是单个合法 JSON 对象, 不要任何 markdown 围栏 (不要 ```json ... ```), 不要前后说明文字。
2. 所有 likert5/likert7 题必须给两端锚点 (anchor_low / anchor_high), 例如 "1=完全不主动 / 5=非常主动"。
3. 所有 number/range 题必须说清单位 + 主动/被动等限定 (在 hint_zh 里), 比如 "TA 每周【主动】(你没开口就提)约你的次数, 单位次/周"。
4. 题目使用生活化中文, 不出现 WACC / DCF / EBITDA / FCF 等金融术语 — 那些是后端引擎的事。
5. 100% 中文, 不夹杂英文。
6. 你的输出会被 Python 引擎机械读取, 严格 JSON 是硬性要求。"""


def _user_template(description: str) -> str:
    desc = (description or "").strip() or "(用户没有提供描述, 假设是一段 3 个月左右的暧昧关系, 自由发挥)"
    ib_param_list = "\n".join(f"  - {k}: {v}" for k, v in IB_PARAMS.items())
    stages_text = "\n".join(f"  {sid}: {label} — {why}" for sid, label, why in SIX_STAGES)
    return f"""【用户描述的估值对象】
---
{desc}
---

【6 个阶段提醒】
{stages_text}

【可用的 IB 参数白名单 (每题必须 mapping 到其中一个)】
{ib_param_list}

【输出 JSON shape】
返回这个结构, 严格按键名 (不要换成 questions/items 等同义词):

{{
  "title_zh": "你给这次估值起的标题, 12 字以内",
  "subtitle_zh": "副标题, 一句话呼应用户描述",
  "subject_kind": "person | crush | relationship | self | other",
  "stages": [
    {{
      "id": "B1",
      "label_zh": "她/他是谁 · 基本盘",
      "why_matters_zh": "为什么这一步重要 (一段话, 给用户解释)",
      "sub_themes": [
        {{
          "name_zh": "子主题名 (你根据描述决定)",
          "why_zh": "这个子主题在这段关系里为什么值得问",
          "fields": [
            {{
              "id": "snake_case_unique_id",
              "label_zh": "题目, 生活化中文",
              "kind": "likert5 | likert7 | number | range | select",
              "hint_zh": "提示文本: 解释含义+举例+主动/被动+单位",
              "anchor_low_zh": "(likert 必填) 最低值的具体含义, 如 '1=完全说不出 TA 喜欢什么'",
              "anchor_high_zh": "(likert 必填) 最高值的具体含义, 如 '5=能写一页人物小传'",
              "min": 1, "max": 5, "step": 1, "default": 3,
              "options": [{{"value": "x", "label_zh": "..."}}],
              "ib_param": "fcf_base",
              "mapping": {{"scale": "linear|inverse|log", "to_min": 0.5, "to_max": 8.0}}
            }}
          ]
        }}
      ]
    }},
    {{ "id": "B2", ... }},
    {{ "id": "B3", ... }},
    {{ "id": "B4", ... }},
    {{ "id": "B5", ... }},
    {{ "id": "B6", ... }}
  ]
}}

【生成要求】
- stages 必须严格 6 个, id 顺序 B1, B2, B3, B4, B5, B6
- 每个 stage 内 2-3 个 sub_themes
- 每个 sub_theme 内 4-6 个 fields
- 总题目数控制在 24-32 题 (输出 token 预算考虑, 不要超)
- 至少要覆盖以下 IB 参数类别 (每类至少 1 题):
  · 价值流: fcf_base / ebit_margin / reinvestment_rate
  · 增长: revenue_growth_y1_3 / revenue_growth_y4_5 / terminal_growth
  · 风险: beta_proxy / wacc_risk_premium / red_flags
  · 价格/资产: investment_cost / book_value / moat / exit_cost / comparable_pe / comparable_pb
- mapping.scale = "inverse" 用于"红旗越多 → moat 越低"这种反向映射
- 你的题目要呼应用户描述里的细节 (如果他们提到异地, 就问异地相关; 提到工作忙, 就问时间挤压; 提到前任, 就问对照前任的感受)

只输出 JSON, 不要其他文本。"""


def build_schema_prompt(description: str) -> list:
    """Build [system, user] messages for the schema-generation call.

    Each call is fully self-contained — no reliance on conversation history.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": _user_template(description)},
    ]


# Generic offline fallback when no LLM is available — covers all 4 IB-param classes.
FALLBACK_SCHEMA = {
    "title_zh": "通用估值问卷",
    "subtitle_zh": "未连接 LLM, 使用通用模板",
    "subject_kind": "other",
    "stages": [
        {
            "id": "B1", "label_zh": "她/他是谁 · 基本盘",
            "why_matters_zh": "先把对方画像画清楚, 才有后面的估值。",
            "sub_themes": [{
                "name_zh": "画像与历史",
                "why_zh": "对方平时是什么样, 历史关系怎样",
                "fields": [
                    {"id": "value_delivered", "label_zh": "TA 每周给你带来的正面价值有多大",
                     "kind": "likert5", "hint_zh": "综合评估: 情绪+陪伴+性吸引力+生活支持等",
                     "anchor_low_zh": "1=几乎没有", "anchor_high_zh": "5=非常多",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "fcf_base", "mapping": {"scale": "linear", "to_min": 0.5, "to_max": 8.0}},
                    {"id": "book_assets", "label_zh": "TA 已经累积下来的硬资产 (性格/履历/共同回忆)",
                     "kind": "likert5", "hint_zh": "稀缺、难以替代的部分",
                     "anchor_low_zh": "1=很少", "anchor_high_zh": "5=非常多",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "book_value", "mapping": {"scale": "linear", "to_min": 1.0, "to_max": 30.0}},
                ],
            }],
        },
        {
            "id": "B2", "label_zh": "走向哪里 · 趋势与预测",
            "why_matters_zh": "捕捉关系势头, 估算未来 12 个月走向。",
            "sub_themes": [{
                "name_zh": "近期与中期趋势",
                "why_zh": "近期 vs 中期不同的成长率",
                "fields": [
                    {"id": "near_growth", "label_zh": "未来 3 个月你期待 TA 的主动度/亲密度会变化多少",
                     "kind": "likert7", "hint_zh": "综合考虑现状趋势",
                     "anchor_low_zh": "1=明显倒退", "anchor_high_zh": "7=飞速进展",
                     "min": 1, "max": 7, "step": 1, "default": 4, "options": [],
                     "ib_param": "revenue_growth_y1_3", "mapping": {"scale": "linear", "to_min": -0.10, "to_max": 0.30}},
                    {"id": "long_growth", "label_zh": "1-3 年后这段关系还能继续升级吗",
                     "kind": "likert5", "hint_zh": "看长期可持续性",
                     "anchor_low_zh": "1=基本不可能", "anchor_high_zh": "5=很有把握",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "terminal_growth", "mapping": {"scale": "linear", "to_min": -0.02, "to_max": 0.05}},
                ],
            }],
        },
        {
            "id": "B3", "label_zh": "相处含金量 · 内在估值",
            "why_matters_zh": "每次相处真正的'含金量', 决定 DCF 的核心。",
            "sub_themes": [{
                "name_zh": "情绪能量与稳定性",
                "why_zh": "见 TA 是回血还是耗血, 状态稳不稳",
                "fields": [
                    {"id": "signal_clarity", "label_zh": "TA 的信号有多清晰 (不模糊不混乱)",
                     "kind": "likert5", "hint_zh": "TA 的喜欢/不喜欢是不是说得清",
                     "anchor_low_zh": "1=完全混乱", "anchor_high_zh": "5=非常清晰",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "ebit_margin", "mapping": {"scale": "linear", "to_min": 0.05, "to_max": 0.45}},
                    {"id": "effort_required", "label_zh": "维持现状每周要花多少精力",
                     "kind": "likert5", "hint_zh": "包括猜心思、安排、维系等",
                     "anchor_low_zh": "1=零负担", "anchor_high_zh": "5=非常累",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "reinvestment_rate", "mapping": {"scale": "linear", "to_min": 0.05, "to_max": 0.6}},
                    {"id": "volatility", "label_zh": "TA 的状态/态度波动有多大",
                     "kind": "likert5", "hint_zh": "今天热情明天冷淡这种",
                     "anchor_low_zh": "1=非常稳", "anchor_high_zh": "5=过山车",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "beta_proxy", "mapping": {"scale": "linear", "to_min": 0.4, "to_max": 2.4}},
                ],
            }],
        },
        {
            "id": "B4", "label_zh": "横向对照 · 市场与先例",
            "why_matters_zh": "和同龄人/前任/类似案例对比, 给出 anchor。",
            "sub_themes": [{
                "name_zh": "可比与先例",
                "why_zh": "同等条件下的市场比价",
                "fields": [
                    {"id": "moat", "label_zh": "TA 在你心里有多 unique (其他人能替代吗)",
                     "kind": "likert5", "hint_zh": "稀缺性",
                     "anchor_low_zh": "1=随时可替代", "anchor_high_zh": "5=独一无二",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "moat", "mapping": {"scale": "linear", "to_min": 0.0, "to_max": 1.0}},
                    {"id": "peer_compare", "label_zh": "在你认识的同 type 人里 TA 排在哪个位置",
                     "kind": "likert5", "hint_zh": "全方位对比",
                     "anchor_low_zh": "1=远低于平均", "anchor_high_zh": "5=Top 5%",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "comparable_pe", "mapping": {"scale": "linear", "to_min": 6.0, "to_max": 30.0}},
                ],
            }],
        },
        {
            "id": "B5", "label_zh": "你的成本与退路",
            "why_matters_zh": "你已投入多少, 还剩多少退路。",
            "sub_themes": [{
                "name_zh": "投入与退出",
                "why_zh": "看清自己真实的承受面",
                "fields": [
                    {"id": "your_invest", "label_zh": "你目前每周在 TA 身上花的时间+情绪+钱 (折合小时)",
                     "kind": "number", "hint_zh": "0-40 小时, 综合估算",
                     "min": 0, "max": 40, "step": 1, "default": 5, "options": [],
                     "ib_param": "investment_cost", "mapping": {"scale": "linear", "to_min": 0.5, "to_max": 60.0}},
                    {"id": "exit_difficulty", "label_zh": "如果现在让你退出, 你能多顺利地退出",
                     "kind": "likert5", "hint_zh": "心理+生活影响综合",
                     "anchor_low_zh": "1=随时优雅退出", "anchor_high_zh": "5=已 all-in 无退路",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "exit_cost", "mapping": {"scale": "linear", "to_min": 0.0, "to_max": 8.0}},
                ],
            }],
        },
        {
            "id": "B6", "label_zh": "压力情景与边界",
            "why_matters_zh": "找出会让判断翻盘的边界条件。",
            "sub_themes": [{
                "name_zh": "红旗与边界",
                "why_zh": "极端情景下你的反应",
                "fields": [
                    {"id": "red_flag_count", "label_zh": "你能数出几个 red flag (撒谎/拖延/三角关系/失约等)",
                     "kind": "number", "hint_zh": "0-10",
                     "min": 0, "max": 10, "step": 1, "default": 0, "options": [],
                     "ib_param": "red_flags", "mapping": {"scale": "linear", "to_min": 0.0, "to_max": 0.25}},
                    {"id": "stress_tolerance", "label_zh": "如果 TA 突然消失一周, 你能承受吗",
                     "kind": "likert5", "hint_zh": "极端情景测试",
                     "anchor_low_zh": "1=完全无法承受", "anchor_high_zh": "5=完全无所谓",
                     "min": 1, "max": 5, "step": 1, "default": 3, "options": [],
                     "ib_param": "wacc_risk_premium", "mapping": {"scale": "inverse", "to_min": 0.0, "to_max": 0.10}},
                ],
            }],
        },
    ],
}
