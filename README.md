# 估值工作台 / Valuation Workbench

[English](README.md) | 中文

> 用华尔街投行的方法 (DCF / P/E / P/B / EPS / 敏感性表 / 前瞻变量 / 投资策略) 给一个人、暧昧对象、一段感情、或者你自己做估值。半严肃 meme 工具。

```bash
python app.py
# 打开 http://127.0.0.1:8782
```

- **纯 Python 标准库** — 零运行依赖, 一行启动。
- **本机优先** — 所有计算都在你这台电脑上完成。不上传, 不联网, 不留 cookie。
- **双语** — 中文 + 英文同一份代码。
- **12+ 篇引用** — Modigliani-Miller, Gordon, Sharpe-Lintner, Damodaran, McKinsey *Valuation* 等。
- **断点续跑** — localStorage 自动保存; 可导出为 JSON 文件分享或恢复。
- **动态表单** — 阶段 (A/B/C/D) 固定, 表单字段根据估值对象动态生成。架构灵感来自 [AI-decision-engine-zh](https://github.com/ZhenyuanPAN822/AI-decision-engine-zh)。
- **前瞻变量** — IB 风格的"如果 X 发生, 估值变多少"敏感性。
- **Bloomberg 风格 tear sheet** — 顶部 hero 读数 + 敏感性热力图 + bear/base/bull 三场景对比。

## 四种估值对象

| 对象 | 字段数 | 适用场景 |
|---|---|---|
| **人** (person) | 9 | 朋友、同事、合作对象、相亲对象 — 快速 screen |
| **暧昧对象** (crush) | 10 | "TA 到底值不值得继续投入" |
| **一段感情** (relationship) | 10 | "应该 hold 还是 cut" — 评估维护成本、退出成本、forward step |
| **自己** (self) | 9 | "我现在值多少" — 技能、人脉、增长率、可选性、健康 |

## 4 阶段工作流

```
A · 选估值对象        →    B · 填动态问卷
                                  ↓
D · 估值报告 (tear sheet) ←  C · 前瞻变量 + 三场景
```

阶段固定, 每阶段的字段根据估值对象动态生成。

## 你能拿到什么

- **顶部读数:** P/E, P/B, EPS, 公允价值 (fair value), 上行/下行 (upside %)
- **DCF:** 5 年现金流贴现 + Gordon 终值
- **敏感性表:** 5×5 表, 变动增长率 g 和折现率 WACC
- **三场景:** bear / base / bull, 围绕你的前瞻变量扰动
- **原型分类:** 8 种之一 — 蓝筹股 / 成长股 / 价值陷阱 / 垃圾债 / 细价股 / 破产清算 / 防御股 / Meme 股
- **投资策略:** 仓位 (LONG/SHORT/FLAT/HEDGE)、持有期、信心 (STRONG_BUY → STRONG_SELL)
- **改进建议:** 3-5 条针对你的原型的可执行 bullet
- **Markdown + JSON 导出**

## 输出 verdict 样例

> **原型: 价值陷阱 (Value Trap)** · 拟合度 72%
>
> > "P/E = 1.99 看起来便宜, 但 E 持续低迷, g 接近 0。
> >  → 仓位 FLAT, 持有期 TERMINATE, 信心 SELL.
> >
> > **改进建议:**
> > 1. 停止增加投入 — 不要被低 PE 误导。
> > 2. 诚实评估: TA 的 E 在过去 6 个月真的有提升迹象吗?如果没有, 这就是 trap。
> > 3. 把节省下来的时间和情感分配到 alt option (备选标的)。"

## 快速开始

```bash
git clone https://github.com/<user>/valuation-workbench
cd valuation-workbench
python app.py
# 打开 http://127.0.0.1:8782
```

或 CLI:

```bash
python app.py --cli --target crush --lang zh --out report.md
```

或 smoke test:

```bash
python scripts/smoke_test.py
```

## 架构

```
valuation_workbench/
├── schemas/                # 每类对象一个 schema (动态表单的根基)
│   ├── person.py
│   ├── crush.py
│   ├── relationship.py
│   └── self_eval.py
├── valuation/
│   ├── core.py             # E / BV / P / g / β / WACC 聚合
│   ├── ratios.py           # P/E, P/B, EPS
│   ├── dcf.py              # 5 年 DCF + Gordon 终值 + 敏感性表
│   ├── archetype.py        # 8 原型分类器
│   └── strategy.py         # 仓位/持有期/信心 + 改进建议
├── forward.py              # bear/base/bull 三场景 + 完整 pipeline
├── session.py              # 保存/加载
├── exporter.py             # Markdown / JSON
└── svg_renderer.py         # tear sheet / 敏感性热力图 / 三场景
```

## 隐私

- HTTP 服务只绑定 `127.0.0.1`。
- 核心代码无任何外部网络调用。
- 只用 localStorage — 你的答案不离开本机。
- 默认进入选择阶段, 不需要任何真实数据。

## 用户友好特性

- **断点续跑** — 每填一个滑块自动保存; 关闭浏览器再打开会自动恢复
- **动态表单** — 字段根据你选的对象类型实时生成
- **前瞻变量** — IB 风格 "if X happens" 自定义场景
- **响应式** — 手机端可用
- **键盘快捷键** — S 保存 / L 加载 / R 重置 / N 下一步 / P 上一步
- **可访问性** — `prefers-reduced-motion` 支持
- **离线可用** — 即使 Google Fonts 被墙也能用 (使用系统字体回退)

## 测试

```bash
python -m pytest tests/ -q
```

49 个测试覆盖: DCF 数值正确性、敏感性表网格、原型可达性、Schema 完备性、前瞻场景、会话往返、SVG 有效性、Markdown 格式、hard-exclusion 合规。

## 引用

- Modigliani-Miller (1958, 1961)
- Gordon (1962) — Gordon 增长模型
- Sharpe-Lintner (1964/1965) — CAPM
- Fama-French (1993) — 三因子
- Damodaran (2002) — *Investment Valuation*
- Koller-Goedhart-Wessels (2020) — McKinsey *Valuation*
- Markowitz (1952), Black-Scholes (1973)
- Tversky-Kahneman (1979) — 前景理论
- Bowlby (1969) — 依恋理论

## 许可

MIT。

## 免责

半严肃 meme 工具, 使用 IB 估值方法做隐喻映射。**不构成财务建议, 不构成恋爱建议, 不是心理咨询。** 结论只描述你输入的参数如何在 IB 方法学下被映射成 valuation — 不对真实的人或真实的关系作任何确定性判断。
