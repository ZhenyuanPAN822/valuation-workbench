# 对象/暧昧估值工作台

> 半严肃的投行级估值工具，**专门给你的对象或暧昧对象做估值**。
> LLM 根据你写的描述个性化生成 6 阶段问卷（对标投行 IPO 估值流程），本地引擎跑三法综合估值 + 蒙特卡洛 P10/P50/P90，最后 LLM 写一份完整的投行风格估值备忘录（投资论点 / 三场景叙事 / Top 3 风险 / 行动清单 / 退出策略）。

```bash
python app.py            # 打开 http://127.0.0.1:8782
```

---

## 目录

- [它能做什么](#它能做什么)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [前置依赖](#前置依赖)
- [快速开始](#快速开始)
- [使用流程（A → B → F → D）](#使用流程a--b--f--d)
- [六阶段问卷详解](#六阶段问卷详解)
- [三法综合估值引擎](#三法综合估值引擎)
- [LLM 集成](#llm-集成)
- [架构总览](#架构总览)
- [HTTP API 端点](#http-api-端点)
- [环境变量](#环境变量)
- [可用脚本](#可用脚本)
- [测试](#测试)
- [键盘快捷键](#键盘快捷键)
- [故障排查](#故障排查)
- [隐私](#隐私)
- [部署](#部署)
- [引用](#引用)
- [许可](#许可)
- [免责](#免责)

---

## 它能做什么

把"TA 到底值不值得我继续投入"这种感性问题，**用投行做 IPO 估值的方法学**走一遍：

1. 你用一段自然语言写下你的对象或暧昧对象的情况（异地、忙、有前任阴影、刚开始、已经在一起一年……）。
2. LLM 把它翻译成一份 30-50 题的个性化问卷，分成 6 个阶段（业务理解 → 趋势预测 → 内在估值 → 横向对照 → 成本与退路 → 压力情景）。每题都用日常语言写（不会出现 WACC、DCF 这种术语），但每题在后台都绑定了一个真正的 IB 参数（FCF、增长率、利润率、可比 P/E、护城河、red flags 等等）。
3. 你填完问卷，本地的纯 Python 引擎把题目映射到 IB 输入，跑：
   - 三阶段 DCF（5 年明确预测 + 5 年线性收敛 + Gordon 终值）
   - 可比公司倍数（P/E + P/B + EV/EBITDA，受护城河调权）
   - 资产 / 重置成本法
   - 三法按你的 archetype 加权混合，得到 fair value 的 low / mid / high 区间
   - 800 次蒙特卡洛扰动，得到 P10 / P50 / P90 + `P(公允价值 > 投入成本)`
4. LLM 看完结果再写一份投行风格的估值备忘录：投资论点、Bull / Base / Bear 三场景叙事、Top 3 风险（触发条件 / 后果 / 早期信号）、本周/本月/本季的行动清单、退出策略、关键假设、横向对照叙事、一句话裁决。
5. 输出 Bloomberg 风格 tear sheet（SVG）+ Markdown 备忘录 + 完整 JSON。所有数据停留在你本机，LLM key 只在浏览器里。

它不是恋爱建议工具，也不是心理咨询。它是把投行估值的鞠躬尽瘁的严肃感，套到一个本来太感性的判断上 —— 强迫你把模糊的感觉拆成可量化的输入，然后看引擎的算术输出会不会让你眼前一亮、或者让你看清自己一直回避的事实。

---

## 核心特性

- **6 阶段动态问卷**（B1-B6）对标投行 IPO 估值流程：业务理解 → 预测建模 → DCF → 可比公司 → LBO 底价 → 压力情景。**阶段固定，子主题由 LLM 根据你的描述生成** —— 异地的会被问异地，工作狂的会被问时间挤压，有前任阴影的会被问对照感受。
- **5 个 LLM 厂商，模型可选**：OpenAI / DeepSeek / Anthropic / Gemini / 任意 OpenAI 兼容自定义 endpoint。每个厂商带预设模型清单 + 自定义模型输入框 + **测试连接探针按钮**。
- **3 个自包含 prompt**（schema / 前瞻变量 / 报告叙事），每次调用都携带全部上下文，兼容那些不保留对话历史的 API 中转站。
- **三法加权综合估值** + 800 次蒙特卡洛 P10/P50/P90，输出公允价值的 low/mid/high 区间。
- **CAPM WACC**：`rf + β·ERP + idiosyncratic premium`，安全护栏 `WACC > terminal_g + 2%`。
- **LLM 自动产出前瞻变量**：看完答案后，LLM 提 2-3 个最关键的"如果 X 发生"候选 + 个性化 rationale + 推荐 Δ%，不让你填空。
- **LLM 投资备忘录**：投资论点 / Bull-Base-Bear 三场景叙事 / Top 3 风险（触发-后果-早期信号）/ 本周-本月-本季行动清单 / 退出策略 / 关键假设 / 横向对照叙事 / 一句话裁决。
- **离线兜底**：不勾选 LLM 也能跑 —— 后端有一份通用 schema，同一套引擎全程跑通，**不需要任何 API key**。
- **历史会话**：`crushValuation.sessions.v1` localStorage，上限 20 条，首页提供继续/删除按钮。
- **明亮主题 + 大字号**：米白底 + 深墨字，基准 17-18 px，全中文界面。
- **键盘快捷键** + **断点续跑**（每填一个滑块自动存 localStorage）+ **导出/导入 JSON**。
- **零运行时依赖**：纯 Python 标准库，LLM 调用走 `urllib`。

---

## 技术栈

| 层 | 选型 |
|---|---|
| **语言** | Python 3.10+（标准库 only） |
| **HTTP 服务** | `http.server.BaseHTTPRequestHandler`（stdlib） |
| **LLM 调用** | `urllib.request`（stdlib） |
| **前端** | 单文件 HTML + 原生 CSS + Vanilla JS（无构建步骤、无 npm） |
| **持久化** | 浏览器 `localStorage`（用户数据从不离开浏览器） |
| **测试** | `pytest`（仅 dev 可选依赖） |
| **打包** | `pyproject.toml` + setuptools |
| **运行环境** | macOS / Linux / Windows，绑定 `127.0.0.1` |

**生产依赖：零。** 全部由 Python 标准库实现。`pytest` 只在跑测试时需要。

---

## 前置依赖

- **Python 3.10+**（dataclass kw_only、`typing` 升级用得到）。`python --version` 查看。
- **任意现代浏览器**（Chrome / Edge / Firefox / Safari），需要支持 `fetch`、`localStorage`、CSS Grid。
- **可选：一个 LLM API key**。下面任意一个都行，没有也能跑（用兜底 schema）：
  - DeepSeek（推荐入门，便宜）：https://platform.deepseek.com
  - OpenAI：https://platform.openai.com
  - Claude：https://console.anthropic.com
  - Gemini：https://aistudio.google.com
  - 任意 OpenAI 兼容 endpoint（中转站、本地 vLLM 等）

---

## 快速开始

```bash
# 1. clone（或直接下载 zip）
git clone https://github.com/<your-username>/valuation-workbench
cd valuation-workbench

# 2. 启动服务（默认 127.0.0.1:8782）
python app.py
```

打开浏览器访问 http://127.0.0.1:8782 ，会看到顶栏的 **Provider / Model / API Key** 选择器：

1. 在顶栏挑一个 provider（默认 DeepSeek），从下拉菜单选 model（或点 "自定义" 输入任意 model 名）；
2. 把 API key 粘进输入框；
3. 点 **测试连接**，看到 `✓ 连接成功` 再继续 —— 这一步会拒掉错 key、错 endpoint、错 model；
4. 进 **阶段 A**，用一段话描述你想估值的对象（一两段话，越具体越好 —— 异地、相处时长、互动节奏、TA 的特点、你的顾虑都写上）；
5. 阶段 B1-B6 LLM 生成的个性化问卷会逐阶段引导你填；
6. 阶段 F LLM 提 2-3 个候选前瞻变量，挑一个；
7. 阶段 D 看完整估值报告（tear sheet + 投资备忘录）。

也可以**不挂 LLM** 直接跑：取消勾选"启用 LLM"，会用兜底 schema（10 题左右的通用版本），一样能跑出完整报告。

### CLI 模式

```bash
python app.py --cli --target crush --lang zh --out report.md
```

CLI 模式用的是固定 4 类目标（person / crush / relationship / self）的硬编码 schema，**不调用 LLM**。适合做快速 screen 或 CI/批处理。

### Smoke 测试

```bash
python scripts/smoke_test.py
```

会跑通 4 种固定目标 + IB-grade dynamic 流程（用 fallback schema），并把示例输出（SVG tear sheet / 敏感性热图 / 三场景对比 / Markdown 报告 / JSON）写到 `sample_outputs/`。

---

## 使用流程（A → B → F → D）

```
   ┌────────────────────────┐
A  │ 描述对象（自由文本）   │ → LLM 生成 6 阶段个性化问卷
   └────────────────────────┘
              ↓
   ┌────────────────────────┐
B1 │ 她/他是谁 · 基本盘     │ ← 业务理解 + 历史财务
B2 │ 走向哪里 · 趋势与预测  │ ← 预测建模
B3 │ 相处含金量 · DCF 视角  │ ← 内在估值 (DCF)
B4 │ 横向对照 · 市场与先例  │ ← 可比公司 + 先例交易
B5 │ 你的成本与退路         │ ← LBO / 清算底价
B6 │ 压力情景与边界         │ ← 敏感性 + 情景分析
   └────────────────────────┘
              ↓
   ┌────────────────────────┐
F  │ 前瞻变量挑选           │ → LLM 提 2-3 个候选
   └────────────────────────┘
              ↓
   ┌────────────────────────┐
D  │ 估值报告（tear sheet） │ ← 三法 + Monte Carlo + LLM 备忘录
   └────────────────────────┘
```

**阶段固定，每阶段问什么由 LLM 根据你的描述决定。** 这意味着两段不同的关系会被问完全不同的问题。

---

## 六阶段问卷详解

| 阶段 | 标签 | 对应 IB workflow | 这一步在判断什么 |
|---|---|---|---|
| **B1** | 她/他是谁 · 基本盘 | 业务理解 + 历史财务 | TA 是什么样的人、过往关系/生活轨迹、剔除节假日和出差等一次性事件后的日常基线 |
| **B2** | 走向哪里 · 趋势与预测 | 预测建模 | 最近 3 个月趋势、亲密层级走向、未来 12 个月你预期会怎样 |
| **B3** | 相处含金量 · 内在估值 | DCF（自由现金流贴现） | 每次相处的情绪能量、稳定性、价值流稳定度 |
| **B4** | 横向对照 · 市场与先例 | 可比公司 + 先例交易 | 和同龄人、你前任、身边类似 type 的人比较，对照成功/失败先例 |
| **B5** | 你的成本与退路 | LBO 估值 / 清算底价 | 你已投入多少、推掉了什么、退出代价、心理仓位 |
| **B6** | 压力情景与边界 | 敏感性 + 情景分析 | 最坏情况下的承受能力、关键拐点、判断会变的边界条件 |

每阶段 LLM 会根据你的描述选 2-3 个子主题，每子主题 4-6 题，整份问卷加起来 **30-50 题**。所有 likert 题强制带两端锚点（"1=完全不主动 / 5=非常主动"），所有数字题强制说清单位。

---

## 三法综合估值引擎

引擎的输入是 **16 个 IB 参数**（`fcf_base`、`revenue_growth_y1_3/y4_5`、`terminal_growth`、`ebit_margin`、`reinvestment_rate`、`book_value`、`comparable_pe/pb/ev_ebitda`、`wacc_risk_premium`、`beta_proxy`、`investment_cost`、`exit_cost`、`red_flags`、`moat`），由前端问卷题目通过 `to_min/to_max` + `linear/inverse/log` 三种刻度映射出来（见 `valuation_workbench/valuation/ib_engine.py:aggregate_ib_inputs`）。

### 1. 三阶段 DCF

```
EV = Σ(FCF_t / (1+WACC)^t)         t = 1..5     # 显式预测
   + Σ(FCF_t / (1+WACC)^t)         t = 6..10    # 线性收敛到 terminal_growth
   + (FCF_11 / (WACC - g_T)) / (1+WACC)^10      # Gordon 终值

WACC = rf + β·ERP + idiosyncratic_risk_premium
       下限 = max(terminal_growth + 2%, 5%)
```

实现见 `valuation_workbench/valuation/ib_engine.py:compute_dcf_3stage`。

### 2. 可比公司倍数

P/E、P/B、EV/EBITDA 三个倍数各自给一个估值，按护城河（`moat`）调权后混合成一个 `multiples_value`。`moat` 越强，越偏向高 P/E 那个估值（成长股/防御股逻辑）。

### 3. 资产 / 重置成本法

`max(book_floor, replacement_cost)`，作为估值下限地板。

### 4. Archetype-weighted 混合

8 种原型（蓝筹股 / 成长股 / 价值陷阱 / 垃圾债 / 细价股 / 破产清算 / 防御股 / Meme 股），按 IB 输入分类后给三法不同权重：

| Archetype | DCF | 可比 | 资产 |
|---|---|---|---|
| 蓝筹股 | 55% | 35% | 10% |
| 成长股 | 70% | 25% | 5% |
| 价值陷阱 | 30% | 30% | 40% |
| 破产清算 | 10% | 20% | 70% |
| ... | ... | ... | ... |

完整权重见 `ib_engine.py:ARCHETYPE_WEIGHTS`。

### 5. 蒙特卡洛 P10/P50/P90

800 次抽样，对增长率、利润率、WACC、β、可比倍数做正态扰动（σ 取参数 5-15%），每次重新走完三法 + 加权，最后取百分位。同时报告 `P(fair_value > investment_cost)`。

实现见 `ib_engine.py:monte_carlo`。

### 6. 敏感性表

5×5 网格，row = `growth (g)`，col = `WACC`，cell = 该 (g, WACC) 下的 fair value。一眼看清楚估值对哪个变量更敏感。

### 7. 前瞻变量 + 三场景

LLM 看完所有答案后提 2-3 个候选前瞻变量（"如果 TA 的前任复合"、"如果你换城市"、"如果工作变忙到连约会都没空"……），每个带：

- `name_zh`：候选名
- `rationale_zh`：为什么这个变量对你这段关系最关键
- `bull_meaning_zh` / `bear_meaning_zh`：往好/坏方向走时具体是什么样
- `delta_pct`：推荐扰动幅度（一般 ±15-30%）
- `perturb_ib_params`：要扰动哪几个 IB 参数（一般 1-3 个）

挑一个之后，引擎跑 bear / base / bull 三个场景，每个场景里把 `perturb_ib_params` 列表里的 IB 参数全部按 `±delta_pct` 扰动（`inverse` 刻度的字段会自动反号，让 bull 永远是"对你更好"那一边），重新跑一遍三法 + Monte Carlo。

---

## LLM 集成

### Provider 一览

| Provider | Endpoint | 默认模型 | 备注 |
|---|---|---|---|
| `openai` | `https://api.openai.com/v1/chat/completions` | `gpt-4o-mini` | 模型清单：gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, o1, o1-mini, o3-mini |
| `deepseek` | `https://api.deepseek.com/chat/completions` | `deepseek-chat` | 模型清单：deepseek-chat, deepseek-reasoner |
| `anthropic` | `https://api.anthropic.com/v1/messages` | `claude-sonnet-4-6` | 模型清单：claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5 |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta` | `gemini-2.5-flash` | 模型清单：gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash |
| `custom` | （用户填） | （用户填） | 任意 OpenAI 兼容 endpoint：中转站、本地 vLLM、Ollama OpenAI-compat 端点 |

每个 provider 都支持 **`__custom__` 哨兵值** —— 切到自定义模型后，UI 弹出文本框让你输任意模型名（适用于厂商发新模型但代码还没更新的情况）。

### 3 个 self-contained prompt

每次调用都重新带全部上下文，**对没有对话记忆的中转站友好**。

| Prompt | 文件 | 输入 | 输出 |
|---|---|---|---|
| Schema 生成 | `valuation_workbench/llm/schema_prompt.py` | 用户 free-text 描述 | 6-stage 个性化 JSON schema (30-50 题) |
| 前瞻变量提案 | `valuation_workbench/llm/forward_prompt.py` | 描述 + schema 摘要 + 答案摘要 + IB 输入摘要 | 2-3 个候选前瞻变量 JSON |
| 报告叙事 | `valuation_workbench/llm/narrative_prompt.py` | 全部上下文 + 估值结果 | 投资论点 / Bull-Base-Bear 叙事 / Top 3 风险 / 行动清单 / 退出策略 / 关键假设 |

### JSON 解析的 3 层兜底

LLM 返回 JSON 时不一定干净（有时带 markdown 围栏 ```json...```、有时前后说一两句废话）。解析层（`valuation_workbench/llm/parser.py`）按这个顺序尝试：

1. 直接 `json.loads`
2. 抠 ```json ... ``` 围栏内容
3. 切最外层的 `{ ... }` 大括号

任一成功即返回；全失败抛 `ParseError`，前端 fallback 到内置 schema。

### 离线 fallback

每个 prompt 都配了一份 fallback 数据（`FALLBACK_SCHEMA` / `FALLBACK_FORWARD` / `fallback_narrative`）。如果用户不挂 LLM、API 不通、JSON 解析失败、或者明确点了"用兜底"按钮，引擎会无缝切换 —— 用户体验仍然连贯，只是问卷不个性化。

### 安全规范

- **API key 只在浏览器**：从 `localStorage` 读，每次请求拼到 POST body 给本地 server，server 转发完立即丢弃，**不持久化、不打日志、不写文件**。
- **server 是透明代理**：`/api/llm` 端点收到 provider/key/model/messages 后调一次 `call_llm`，把结果原样返回。
- **键盘 + UI 都不会回显 key**：`<input type="password" autocomplete="off">`。

---

## 架构总览

```
repo/
├── app.py                          # HTTP 服务 + CLI 入口（单文件包含全部前端 HTML/CSS/JS）
├── pyproject.toml                  # 包元信息（零运行依赖）
├── .env.example                    # 可选环境变量（host/port）
├── LICENSE                         # MIT
├── README.md / README.zh-CN.md     # 这份文档
│
├── valuation_workbench/            # 核心库
│   ├── __init__.py                 # 公共 API + 12 篇引用
│   ├── models.py                   # 全部 frozen dataclass：SchemaField / Schema / IBInputs /
│   │                                 DCF3StageResult / MultiplesResult / AssetResult /
│   │                                 BlendedValuation / MonteCarloResult / DynamicField /
│   │                                 DynamicSubtheme / DynamicStage / DynamicSchema /
│   │                                 ForensicsReport / Session
│   ├── dynamic_schema.py           # LLM JSON → DynamicSchema 解析器（含 CANONICAL_IB_RANGES）
│   ├── forward.py                  # 三场景构建 + run_pipeline (固定流) + run_pipeline_ib (IB 流)
│   ├── session.py                  # 会话保存/加载
│   ├── exporter.py                 # Markdown / JSON 导出
│   ├── svg_renderer.py             # tear sheet / 敏感性热图 / 三场景对比 SVG 渲染
│   │
│   ├── llm/                        # LLM 集成层
│   │   ├── __init__.py
│   │   ├── providers.py            # 5 厂商分发 + probe_connection + CUSTOM_MODEL_SENTINEL
│   │   ├── parser.py               # 3 层 JSON 解析兜底
│   │   ├── schema_prompt.py        # IB_PARAMS + SIX_STAGES + FALLBACK_SCHEMA + 系统/用户 prompt
│   │   ├── forward_prompt.py       # 前瞻变量 prompt + FALLBACK_FORWARD
│   │   └── narrative_prompt.py     # 报告叙事 prompt + fallback_narrative
│   │
│   ├── schemas/                    # 固定流的 4 类目标 schema
│   │   ├── __init__.py
│   │   ├── person.py               # 人 (9 字段)
│   │   ├── crush.py                # 暧昧对象 (10 字段)
│   │   ├── relationship.py         # 一段感情 (10 字段)
│   │   └── self_eval.py            # 自己 (9 字段)
│   │
│   └── valuation/                  # 估值引擎
│       ├── __init__.py
│       ├── core.py                 # E / BV / P / g / β / WACC 聚合（固定流）
│       ├── ratios.py               # P/E、P/B、EPS
│       ├── dcf.py                  # 5 年 DCF + Gordon TV + 5×5 敏感性
│       ├── archetype.py            # 8 原型分类器（含 classify / classify_ib）
│       ├── strategy.py             # 仓位 / 持有期 / 信心 + 改进建议
│       └── ib_engine.py            # IB-grade 引擎：aggregate_ib_inputs / compute_dcf_3stage /
│                                     compute_multiples / compute_asset / blend_valuations /
│                                     monte_carlo + ARCHETYPE_WEIGHTS
│
├── tests/                          # 81 个 pytest 测试
│   ├── test_archetype.py
│   ├── test_compatibility.py       # hard-exclusion + zero-runtime-deps 守门
│   ├── test_core.py
│   ├── test_dcf.py
│   ├── test_exporter.py
│   ├── test_forward.py
│   ├── test_ib_engine.py
│   ├── test_llm_parser.py
│   ├── test_ratios.py
│   ├── test_schemas.py
│   ├── test_session.py
│   ├── test_strategy.py
│   ├── test_svg.py
│   └── test_v3_schema.py           # 6-stage parser / multi-vendor / 自包含 prompt
│
├── scripts/
│   └── smoke_test.py               # E2E 烟雾测试 + 重新生成 sample_outputs/
│
└── sample_outputs/                 # 样本输出（被 smoke_test 重新生成）
    ├── sample-tear-sheet.svg          # 固定流样本
    ├── sample-sensitivity.svg
    ├── sample-scenarios.svg
    ├── sample-report.md
    ├── sample-ib-tear-sheet.svg       # IB 流样本
    ├── sample-ib-sensitivity.svg
    ├── sample-ib-scenarios.svg
    ├── sample-ib-report.md
    └── sample-ib-report.json
```

### 数据流（IB 流）

```
浏览器                                本地 HTTP server (app.py)              LLM API
  │                                            │                                │
  │  GET /                                     │                                │
  │ ─────────────────────────────────────────► │                                │
  │ ◄─────────── 单文件 HTML（含 CSS/JS）       │                                │
  │                                            │                                │
  │  POST /api/probe                           │                                │
  │  {provider, key, model, [endpoint]}        │                                │
  │ ─────────────────────────────────────────► │                                │
  │                                            │  call_llm("请回复'连接成功'")  │
  │                                            │ ─────────────────────────────► │
  │                                            │ ◄─────── 测试响应             │
  │ ◄────── {ok, content} 或 {ok:false,error} │                                │
  │                                            │                                │
  │  POST /api/gen_schema                      │                                │
  │  {provider, key, model, description}       │                                │
  │ ─────────────────────────────────────────► │                                │
  │                                            │  call_llm(schema_prompt)       │
  │                                            │ ─────────────────────────────► │
  │                                            │ ◄─────── JSON schema (30-50题)│
  │                                            │  parse_dyn_schema (canonical)  │
  │ ◄────── DynamicSchema (6 stages)          │                                │
  │                                            │                                │
  │  填阶段 B1-B6 → localStorage 自动保存      │                                │
  │                                            │                                │
  │  POST /api/forward                         │                                │
  │  {description, schema, answers}            │                                │
  │ ─────────────────────────────────────────► │                                │
  │                                            │  call_llm(forward_prompt)      │
  │                                            │ ─────────────────────────────► │
  │                                            │ ◄─── 2-3 候选前瞻变量          │
  │ ◄────── candidates[]                       │                                │
  │                                            │                                │
  │  POST /api/compute_full                    │                                │
  │  {description, schema, answers,            │                                │
  │   forward_choice, ...}                     │                                │
  │ ─────────────────────────────────────────► │                                │
  │                                            │  run_pipeline_ib (本地)        │
  │                                            │  → 三法 + Monte Carlo          │
  │                                            │  call_llm(narrative_prompt)    │
  │                                            │ ─────────────────────────────► │
  │                                            │ ◄─── thesis/scenarios/risks/.. │
  │ ◄────── 完整 ForensicsReport (含 IB 字段) │                                │
  │                                            │                                │
  │  渲染 tear sheet + 备忘录                  │                                │
  │                                            │                                │
```

---

## HTTP API 端点

所有端点都在 `127.0.0.1:8782`，POST 用 JSON body。

| Method | Path | Body | 返回 |
|---|---|---|---|
| GET | `/` | — | 单文件 HTML（含全部前端） |
| POST | `/api/probe` | `{provider, api_key, model, endpoint?}` | `{ok: bool, content?: str, error?: str}` |
| POST | `/api/gen_schema` | `{provider, api_key, model, description, endpoint?}` | `DynamicSchema` JSON 或 fallback |
| POST | `/api/forward` | `{description, schema, answers, provider, api_key, model, endpoint?}` | `{candidates: [...], explanation_zh: str}` |
| POST | `/api/compute_full` | `{description, schema, answers, forward_choice, provider?, api_key?, model?, endpoint?}` | 完整 `ForensicsReport` JSON（含 ib_inputs / dcf3 / multiples / blended / mc + LLM 备忘录） |
| POST | `/api/save_session` | `Session` JSON | `{ok: true}` |
| POST | `/api/export_md` | `ForensicsReport` JSON | Markdown 文本 |
| POST | `/api/export_json` | `ForensicsReport` JSON | 原样回显（前端用 `<a download>` 触发下载） |

server 不缓存任何用户数据 —— `SESSION_CACHE` 只用于跨请求传递 schema 和报告，重启即清。

---

## 环境变量

`.env.example` 里全部都是**可选**配置：

| 变量 | 默认 | 说明 |
|---|---|---|
| `VALUATION_HOST` | `127.0.0.1` | HTTP 服务监听地址。**强烈建议保持 127.0.0.1**（本机访问），改成 `0.0.0.0` 会暴露到局域网。 |
| `VALUATION_PORT` | `8782` | HTTP 服务端口 |

**没有任何必填环境变量。** API key 不通过环境变量传入 —— 它由浏览器持有，每次请求时从前端送给后端透传。

---

## 可用脚本

| 命令 | 说明 |
|---|---|
| `python app.py` | 启动 HTTP 服务（默认 http://127.0.0.1:8782） |
| `python app.py --cli --target crush --lang zh --out report.md` | CLI 模式：跑固定 schema → 写 Markdown 报告（**不调 LLM**） |
| `python app.py --cli --target self --lang en --out self.md` | 同上，估值"自己"，输出英文 |
| `python -m pytest tests/ -q` | 跑全部 81 个测试 |
| `python -m pytest tests/test_ib_engine.py -v` | 跑 IB 引擎测试，verbose |
| `python scripts/smoke_test.py` | 端到端烟雾测试 + 重新生成 sample_outputs/ |

CLI 支持的 `--target`：`person` / `crush` / `relationship` / `self`。
CLI 支持的 `--lang`：`zh` / `en`。

---

## 测试

```bash
python -m pytest tests/ -q
# 期望输出：........... 81 passed in 0.X s
```

**14 个测试文件，81 个测试。** 测试覆盖：

- DCF 数值正确性（5 年贴现 + Gordon 终值边界条件）
- 三阶段 DCF 守门（fade 段单调、终值小于 5 年贴现 × 上限因子）
- 敏感性表 5×5 grid 完整性
- 三法混合权重正负、low ≤ mid ≤ high 不变量
- 蒙特卡洛收敛（800 次抽样后 P10/P50/P90 顺序、prob_above_cost ∈ [0,1]）
- 8 种 archetype 全部可达
- 4 类固定 schema 字段完备 + 默认值合法
- DynamicSchema 6-stage 解析（嵌套 mapping / 平铺 mapping 双兼容、CANONICAL_IB_RANGES override）
- LLM JSON 解析 3 层兜底（直接 / 围栏 / 大括号切片）
- 多厂商 PROVIDERS 完整性 + probe_connection 合约
- 3 个 prompt 自包含性（每个 prompt 独立含全部上下文）
- Session 保存/加载 round-trip
- SVG 输出格式有效性
- Markdown 导出格式
- Hard-exclusion 合规（生产代码不出现 chat-log/聊天记录/OHLC/candlestick）
- pyproject 零运行依赖守门

---

## 键盘快捷键

- `S` — 保存当前会话
- `L` — 加载会话
- `R` — 重置当前会话
- `N` — 下一阶段
- `P` — 上一阶段

支持 `prefers-reduced-motion` —— 系统设置开了"减少动画"会自动关掉所有过渡动画。

---

## 故障排查

### 连接测试失败 "✗ HTTP 401"
API key 错了。重新去厂商后台拷一遍。**Anthropic 的 key 是 `sk-ant-` 开头**，OpenAI/DeepSeek 是 `sk-` 开头，Gemini 是 `AIza` 开头。

### 连接测试失败 "✗ HTTP 404"
endpoint 错了。如果用自定义 provider，检查 endpoint 末尾是不是 `/v1/chat/completions`（OpenAI 兼容必须有这个完整路径）。

### 连接测试失败 "✗ 网络错误"
要么墙，要么 endpoint 域名不通。挂代理后重试 —— 因为是 stdlib `urllib`，会自动读 `HTTPS_PROXY` / `HTTP_PROXY` 环境变量。

### 阶段 B 没生成问卷，看到的是兜底 10 题
LLM 返回的 JSON 解析失败了。打开 server 控制台看错误栈。最常见原因：
1. max_tokens 不够，schema 被截断 —— 默认值 8000 一般够用
2. 模型不擅长 JSON（gemini-2.0-flash 偶尔会塞 markdown 进去）—— 换 `gemini-2.5-flash` 或 `deepseek-chat`
3. API 中转站插入了广告/水印 —— 换直连或换站

### 阶段 D 报告里 bear / base / bull 三场景数值完全一样
说明前瞻变量没生效。检查 `forward_choice.perturb_ib_params` 是不是空数组。如果 LLM 没产出这个字段，引擎不知道扰动哪个 IB 参数 —— 此时 fallback 是只扰动单个题目，效果较弱。换更强的模型重试。

### 端口占用 "OSError: [Errno 48] Address already in use"
8782 被占。改环境变量 `VALUATION_PORT=8888` 或杀掉旧进程。

### Windows: 浏览器选 model 时下拉看不全
v0.3.1 已经把所有 `<select>` 替换成自定义 `.cdrop` 组件解决了 Chrome/Win 渲染 bug。如果还出现，硬刷一下（Ctrl+Shift+R）清缓存。

### 报告里 archetype 一直是"破产清算"
说明你的输入让 IB 参数全部贴在下界（`investment_cost=0.5`、`fcf_base=0.325`、`book_value=1.0`……）。这是 v0.3.1 之前的 bug —— LLM 给的 `to_min/to_max` 范围和引擎期望的 canonical 范围不匹配，schema round-trip 时被拍平到默认值。`dynamic_schema.py:CANONICAL_IB_RANGES` 已经强制覆盖 LLM 的 mapping，按理不会再出现。如果你看到这个，请提 issue。

---

## 隐私

- HTTP 服务**只绑定 `127.0.0.1`**（除非你手动改 `VALUATION_HOST`），外网访问不到。
- 核心代码（`valuation_workbench/`）**零外部网络调用**，所有计算在你电脑上。LLM 调用是单独走 `app.py:_handle_llm_*`，明确可见。
- API key 只在**浏览器 localStorage**。每次请求转一道，server **不持久化、不打日志、不写盘**。
- 用户答案存浏览器 `localStorage`（key: `crushValuation.sessions.v1`）。**关掉浏览器或清缓存就没了**。
- 服务端 `SESSION_CACHE` 是内存字典，进程退出即清空。
- **不发任何 telemetry，不调 Google Analytics，不嵌任何第三方 JS。** 唯一的对外网络出口是你显式触发的那次 LLM 调用。

如果要 100% 离线，启动时不勾选"启用 LLM"即可。

---

## 部署

**这是一个本地工具，最佳部署方式是不部署。** 在你自己的电脑上跑就好。

如果非要远端跑（比如放公司内网做团队 demo），用 Docker：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
ENV VALUATION_HOST=0.0.0.0
ENV VALUATION_PORT=8782
EXPOSE 8782
CMD ["python", "app.py"]
```

```bash
docker build -t valuation-workbench .
docker run -p 8782:8782 valuation-workbench
```

**注意事项：**
- 如果走公网，前面**必须**套反代 + HTTPS（Caddy / nginx + Let's Encrypt），server 自身没做 TLS。
- API key 仍然在浏览器持有，server 端不持久。但 HTTP 中间层（反代日志、网关）可能记录请求 body —— 想避免，启用 HTTPS 并审计中间层日志策略。
- 默认 `VALUATION_HOST=127.0.0.1` 是安全护栏。改成 `0.0.0.0` 时务必加防火墙规则限制访问源 IP。

---

## 引用

方法学源自这些经典文献：

- Modigliani, F., Miller, M. H. (1958). The Cost of Capital, Corporation Finance and the Theory of Investment. *American Economic Review*, 48, 261–297.
- Modigliani, F., Miller, M. H. (1961). Dividend Policy, Growth, and the Valuation of Shares. *Journal of Business*, 34, 411–433.
- Gordon, M. J. (1962). *The Investment, Financing, and Valuation of the Corporation*. Irwin.
- Sharpe, W. F. (1964). Capital Asset Prices: A Theory of Market Equilibrium. *Journal of Finance*, 19, 425–442.
- Lintner, J. (1965). The Valuation of Risk Assets. *Review of Economics and Statistics*, 47, 13–37.
- Fama, E. F., French, K. R. (1993). Common risk factors in returns. *Journal of Financial Economics*, 33, 3–56.
- Damodaran, A. (2002). *Investment Valuation: Tools and Techniques for Determining the Value of Any Asset*. Wiley.
- Koller, T., Goedhart, M., Wessels, D. (2020). *Valuation: Measuring and Managing the Value of Companies* (McKinsey & Co).
- Markowitz, H. (1952). Portfolio Selection. *Journal of Finance*, 7, 77–91.
- Black, F., Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. *Journal of Political Economy*, 81, 637–654.
- Tversky, A., Kahneman, D. (1979). Prospect Theory. *Econometrica*, 47, 263–291.
- Bowlby, J. (1969). *Attachment and Loss, Vol. 1*. Basic Books.

---

## 许可

MIT。

---

## 免责

半严肃 meme 工具，使用投行估值方法做隐喻映射。

**不构成财务建议，不构成恋爱建议，不构成心理咨询。**

结论只描述你输入的参数如何在 IB 方法学下被映射成 valuation 数值 —— 它不会、也不能对真实的人或真实的关系作任何确定性判断。把它当一面镜子用：那些你说不清的感觉，被强迫拆成可量化的输入再算回来时，可能让你看见一直回避的事实。仅此而已。
