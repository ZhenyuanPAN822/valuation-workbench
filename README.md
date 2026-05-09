# Valuation Workbench｜对象估值工作台

> 我们把 Goldman Sachs、Lazard、KKR 等顶级投行 / 私募常用的估值思路，改造成了给前任、对象、暧昧对象、暗恋对象的「投行级感情估值工具」。
> 系统会根据你估值的对象类型、关系阶段和共同经历，动态生成一份专属的个性化问卷以及调整估值方法。

> 你可以把它理解成：用 DCF、可比倍数、资产法、情景分析、敏感性分析和投资备忘录，重新回答那个很难开口的问题——**TA 到底还值不值得继续投入？**

> 免责声明：本项目不与 Goldman Sachs、Lazard、KKR 或任何金融机构存在官方关联、合作或背书。上面的机构名称仅用于说明产品灵感来自公开金融估值框架与投研表达方式。本项目不是情感建议、投资建议或心理咨询。

---

## 这是什么？

Valuation Workbench 是一个本地运行的「关系估值」工作台。

它会根据你描述的对象或关系，生成一套 6 阶段问卷；你填完之后，系统会把答案转换成一组类投行估值假设，再输出一份结构化报告。

你可以用它评估：

- 暧昧对象：要不要继续投入时间和情绪？
- 暗恋对象：这笔长期项目还有没有 upside？
- 现任对象：关系质量、风险、成长性怎么样？
- 前任：这是不是一个 value trap？
- 自己：把自己当成一家公司，看看基本面如何。

它会帮你把情绪问题拆成可以讨论的指标：投入、回报、风险、成长、替代选项、退出成本。

---

## 你会得到什么？

一份完整报告通常包括：

- 综合估值结论
- DCF / 可比倍数 / 资产法三类估值结果
- Bull / Base / Bear 情景
- Monte Carlo 区间
- 敏感性分析
- 对象类型判断，例如 blue chip、growth、value trap、distressed 等
- 投资策略：LONG / FLAT / SHORT / HEDGE
- 关键风险、行动建议、退出信号
- 可导出的 Markdown、JSON 和 SVG 图表

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/ZhenyuanPAN822/valuation-workbench.git
cd valuation-workbench
```

### 2. 启动本地网页

```bash
python app.py
```

然后打开：

```text
http://127.0.0.1:8782
```

项目默认使用 Python 标准库，不需要先安装一堆依赖。

---

## 推荐使用方式

### Step 1：选择 AI Provider

打开页面后，先在顶部配置模型。

支持：

- OpenAI
- DeepSeek
- Anthropic / Claude
- Google Gemini
- 自定义 OpenAI-compatible API

如果你只是想本地试一下，也可以不启用 LLM。系统会使用内置的 fallback 问卷模板。

### Step 2：描述你要估值的对象

你可以写得很互联网一点，也可以写得很认真。

例如：

```text
我们认识 4 个月，线下见过 3 次。他回复速度不稳定，偶尔很热情，偶尔消失。我们有共同朋友，但没有明确关系定义。我每周大概花 5 小时在这段关系上，情绪波动比较大。
```

系统会根据这段描述生成一套更贴合场景的问卷。

### Step 3：填写 6 阶段问卷

问卷会围绕 6 个阶段展开：

1. 资产盘点：这段关系现在有什么基本面？
2. 收益质量：TA 带来的正向反馈是否稳定？
3. 增长假设：未来有没有可能变好？
4. 风险披露：红旗、波动、沉没成本在哪里？
5. 可比对象：有没有替代选项或更优机会？
6. 交易建议：继续、观望、止损还是对冲？

你不需要懂金融。问题会尽量以日常语言出现，系统会在背后把答案映射为估值参数。

### Step 4：选择前瞻变量

问卷结束后，系统会给你一些可能影响估值的未来变量。

例如：

- TA 是否主动推进关系
- 沟通频率是否改善
- 未来 30 天是否有实质行动
- 红旗是否继续放大
- 你自己的替代选择是否变多

这些变量会进入最终估值模型。

### Step 5：生成报告

最后系统会输出一份完整的「感情估值报告」。

你可以直接在页面里看，也可以导出：

- `.md`：适合复制、发给朋友、继续编辑
- `.json`：适合二次开发或存档
- `.svg`：适合截图、做图、发社交平台

---

## CLI 用法

如果你不想打开网页，也可以直接用命令行生成报告：

```bash
python app.py --cli --target crush --lang zh --out report.md
```

可选 target 包括：

```text
person
crush
relationship
self
```

---

## 它是怎么估值的？

这个项目把关系问题拆成几类类金融指标。

| 关系里的问题 | 模型里的近似指标 |
| --- | --- |
| TA 是否持续提供情绪价值 | free cash flow / earnings quality |
| 互动是否越来越好 | revenue growth / growth rate |
| 关系是否稳定 | WACC / beta / risk premium |
| 有没有明显红旗 | downside adjustment |
| 你投入了多少时间情绪 | investment cost |
| 分开会不会很痛 | exit cost |
| TA 是否稀缺 | moat / scarcity premium |
| 有没有更好选择 | comparable multiples / opportunity cost |

目前主要包含三类估值方法：

1. **DCF：现金流折现**
   把未来可能带来的情绪收益、陪伴价值、关系增量折现到今天。

2. **可比倍数法**
   用类似 P/E、P/B、EV/EBITDA 的方式，把对象放到同类关系样本里看贵不贵。

3. **资产 / 重置成本法**
   估算这段关系已经沉淀的记忆、信任、共同经历、社交网络和重新开始的成本。

最终系统会根据对象类型和风险结构做加权，给出一个 blended fair value。

---

## 项目结构

```text
valuation-workbench/
├── app.py                         # 本地 Web UI、API、CLI 入口
├── valuation_workbench/
│   ├── llm/                       # 多模型 Provider、Prompt、JSON Parser
│   ├── schemas/                   # 内置 person / crush / relationship / self 问卷
│   ├── valuation/                 # DCF、倍数法、资产法、策略、类型判断
│   ├── dynamic_schema.py          # LLM 动态问卷校验与标准化
│   ├── exporter.py                # Markdown / JSON 导出
│   ├── forward.py                 # 前瞻变量与完整估值流水线
│   ├── models.py                  # 核心数据结构
│   ├── session.py                 # 本地 session 保存 / 读取
│   └── svg_renderer.py            # SVG 图表渲染
├── scripts/
│   └── smoke_test.py              # 端到端冒烟测试
├── tests/                         # 单元测试
├── sample_outputs/                # 示例报告与图表
├── pyproject.toml
└── README.md
```

---

## 本地隐私说明

这个项目默认本地运行。

需要注意：

- 页面运行在 `127.0.0.1`
- API Key 存在浏览器 `localStorage`
- 如果启用 LLM，你输入的描述和问卷上下文会发送给你选择的模型服务商
- 如果关闭 LLM，系统会使用本地 fallback 模板，不调用外部模型
- 导出的报告只会在你主动导出时生成

---

## 常见问题

### 这个项目真的能判断一个人值不值得吗？

不能。

它只能帮你把模糊感受结构化，把「我觉得不对劲」拆成更具体的风险、假设和行动建议。最后决定还是你自己做。

### 不配置 API Key 能玩吗？

可以。

不开 LLM 时，系统会使用内置问卷模板；配置 LLM 后，问卷和最终叙事会更贴近你的描述。

### 为什么用投行语言讲感情？

因为很多关系问题本质上都绕不开几个问题：

- 我投入了多少？
- 我得到了什么？
- 风险是不是越来越大？
- 未来还有没有增长？
- 退出成本是不是已经高到离谱？

金融语言不是答案，只是一套好用的拆解工具。

---

## 引用 / References

方法学源自这些经典文献：

- Modigliani, F., Miller, M. H. (1958). The Cost of Capital, Corporation Finance and the Theory of Investment. *American Economic Review*, 48, 261–297.
- Modigliani, F., Miller, M. H. (1961). Dividend Policy, Growth, and the Valuation of Shares. *Journal of Business*, 34, 411–433.
- Gordon, M. J. (1962). *The Investment, Financing, and Valuation of the Corporation*. Irwin.
- Sharpe, W. F. (1964). Capital Asset Prices: A Theory of Market Equilibrium. *Journal of Finance*, 19, 425–442.
- Lintner, J. (1965). The Valuation of Risk Assets. *Review of Economics and Statistics*, 47, 13–37.
- Markowitz, H. (1952). Portfolio Selection. *Journal of Finance*, 7, 77–91.
- Black, F., Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. *Journal of Political Economy*, 81, 637–654.
- Fama, E. F., French, K. R. (1993). Common risk factors in returns on stocks and bonds. *Journal of Financial Economics*, 33, 3–56.
- Damodaran, A. (2002). *Investment Valuation: Tools and Techniques for Determining the Value of Any Asset*. Wiley.
- Koller, T., Goedhart, M., Wessels, D. (2020). *Valuation: Measuring and Managing the Value of Companies* (McKinsey & Co).
- Tversky, A., Kahneman, D. (1979). Prospect Theory: An Analysis of Decision under Risk. *Econometrica*, 47, 263–291.
- Bowlby, J. (1969). *Attachment and Loss, Vol. 1: Attachment*. Basic Books.

---

## 许可

MIT License。
