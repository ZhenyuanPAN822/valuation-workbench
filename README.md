# 对象/暧昧估值工作台 · Crush & Partner Valuation Workbench  ·  v0.3

English | [中文](README.zh-CN.md)

> A half-serious investment-banking-grade valuation tool **specifically for valuing your partner or crush**. The LLM personalizes a 6-stage questionnaire (modelled on the IPO valuation workflow: business understanding → historical → forecast → DCF → comparables → stress-test), the local engine runs three-method valuation with Monte-Carlo P10/P50/P90, and the LLM writes a full IB-style memo (thesis, bull/base/bear narratives, top risks, action plan, exit strategy).

```bash
python app.py            # http://127.0.0.1:8782
```

## What's new in v0.3

- **Focused product**: now specifically for **对象 / 暧昧对象** (partners and crushes), not "anything"
- **6-stage dynamic flow** (B1–B6) modelled on canonical IB IPO valuation: 她是谁 → 走向哪里 → 相处含金量 → 横向对照 → 成本与退路 → 压力情景
- **LLM decides sub-themes within each stage** — two valuations of two different relationships will get genuinely different question structures (long-distance vs busy-job vs ex-shadow each get tailored sub-themes)
- **Full provider/model picker** mirroring AI-decision-engine-zh: each provider has a preset model list + custom model textbox + custom OpenAI-compatible endpoint + **test-connection probe button**
- **Self-contained prompts** (3 calls — schema, forward variables, narrative) — every call carries full context, safe against API gateways that don't preserve conversation history
- **LLM-generated investment memo** in the report: thesis, bull/base/bear narratives, top-3 risks (trigger / consequence / early signal), week / month / quarter action lists, exit strategy, key assumptions, comparable narrative
- **Auto-derived forward variables** — LLM proposes 2-3 candidate forward variables with personalized rationale and recommended Δ%, instead of asking the user to type them
- **Light theme + larger fonts** — cream/parchment background, ink text, 17–18px base, no English mixing
- **Session history** — `crushValuation.sessions.v1` localStorage, cap 20, with Continue/Delete buttons on home

## What stayed from v0.2

- **LLM-driven dynamic schema** — Stage A is a free-text textarea; an LLM converts your description into 8–12 user-friendly proxy questions whose every field is bound to a real IB parameter (FCF / growth / margin / WACC risk premium / comparable P/E / book value / moat / red flags …). Pattern lifted from [AI-decision-engine-zh](https://github.com/ZhenyuanPAN822/AI-decision-engine-zh) — keys live in the browser, server is a thin proxy.
- **Multi-vendor LLM** — DeepSeek, OpenAI, Anthropic, Gemini, or any OpenAI-compatible custom endpoint. Switchable per session.
- **Three-method blended valuation** — three-stage DCF (5y explicit + 5y fade + Gordon terminal) **+** comparables (P/E + P/B + EV/EBITDA, moat-tuned) **+** asset floor; archetype-weighted blend with low / mid / high range.
- **CAPM WACC** — `rf + β · ERP + idiosyncratic risk premium`, with safety floor `> terminal_g + 2%`.
- **Monte-Carlo P10 / P50 / P90** — 800 iterations perturbing growth, margin, WACC, beta, comparables; reports `P(fair > cost)`.
- **Fallback works offline** — uncheck "use LLM" and a 10-question generic schema runs the same engine. No key needed to try.

## Stays the same from v0.1

- **Pure Python stdlib** — zero runtime dependencies; LLM calls use `urllib`.
- **Local-first** — all computation on your machine; LLM keys held by your browser, never logged server-side.
- **Bilingual** — English + 中文.
- **12+ canonical citations** — Modigliani-Miller, Gordon, Sharpe-Lintner, Markowitz, Damodaran, McKinsey *Valuation*, Fama-French, Black-Scholes, Tversky-Kahneman, Bowlby.
- **Session-resumable** — auto-save to localStorage; export/import as JSON.
- **Forward-looking variable** — name the one event that matters; the engine perturbs it ±Δ% across bear/base/bull.
- **Bloomberg-style tear sheet** — hero readouts, P10/P50/P90 fair-value range, three-method breakdown, sensitivity heatmap, scenario comparison.

## Four Valuation Targets

| Target | Schema | Use case |
|---|---|---|
| **Person** | 9 fields (reliability, competence, network, red flags, …) | Quick screen any person |
| **Crush** | 10 fields (response quality, exclusivity, commitment signals, your weekly hours, …) | "Should I keep investing in this 暧昧 thing?" |
| **Relationship** | 10 fields (conflict frequency, repair quality, growth alignment, exit cost, …) | "Should I stay in this relationship?" |
| **Self** | 9 fields (skill quality, network, runway, growth rate, optionality, …) | Honest self-valuation |

## The 4-Stage Workflow

```
A · Pick target type     →   B · Dynamic questionnaire
                                      ↓
D · Tear-sheet review    ←   C · Forward-looking variable + scenarios
```

Stages are fixed; the fields per stage are dynamically generated per target type.

## What You Get

- **Hero readouts:** P/E, P/B, EPS, fair value, upside %
- **DCF:** 5-year discounted cash flow + Gordon terminal value
- **Sensitivity table:** 5×5 grid varying growth (g) × discount rate (WACC)
- **Three scenarios:** bear / base / bull, perturbing your forward-looking variable
- **Archetype classification:** one of 8 — Blue Chip, Growth, Value Trap, Junk Bond, Penny Stock, Distressed, Defensive, Meme
- **Investment strategy:** position (LONG/SHORT/FLAT/HEDGE), hold period, conviction (STRONG_BUY → STRONG_SELL)
- **Improvement recommendations:** 3-5 actionable bullets specific to your archetype
- **Markdown + JSON export**

## Sample Verdict

> **Archetype: Distressed Asset** (fit 78%)
>
> M/M/1 ρ = ... wait, that's a different repo. Here:
>
> > "DCF 显示公允价值 12.3 vs 你目前的 P 47 → 下行 −74%。
> >  Eroding earnings + 高 P → SHORT, TERMINATE, STRONG_SELL.
> >
> > **改进建议:**
> > 1. 立即停止追加投入。
> > 2. 评估退出成本 (exit cost), 选择最低成本路径离场。
> > 3. 做事后复盘: 当初哪些信号被你忽视了?"

## Quick Start

```bash
git clone https://github.com/<user>/valuation-workbench
cd valuation-workbench
python app.py
# open http://127.0.0.1:8782
```

CLI:

```bash
python app.py --cli --target crush --lang zh --out report.md
```

Smoke test:

```bash
python scripts/smoke_test.py
```

## Architecture

```
valuation_workbench/
├── schemas/                # per-target schemas (person/crush/relationship/self)
│   ├── base                # SchemaField base
│   ├── person.py
│   ├── crush.py
│   ├── relationship.py
│   └── self_eval.py
├── valuation/
│   ├── core.py             # E/BV/P/g/β/WACC aggregation
│   ├── ratios.py           # P/E, P/B, EPS
│   ├── dcf.py              # 5-year DCF + Gordon TV + sensitivity table
│   ├── archetype.py        # 8-archetype classifier
│   └── strategy.py         # position/hold/conviction + improvements
├── forward.py              # bear/base/bull scenarios + full pipeline
├── session.py              # save/load
├── exporter.py             # Markdown / JSON
└── svg_renderer.py         # tear sheet, sensitivity heatmap, scenarios
```

## Privacy

- HTTP server binds to `127.0.0.1` only.
- Zero outbound network calls in core code.
- localStorage only — your answers never leave your machine.
- Synthetic-default landing — Stage A picks a target with no data needed.

## Keyboard Shortcuts

- `S` — save session, `L` — load, `R` — reset
- `N` — next stage, `P` — previous stage

## Testing

```bash
python -m pytest tests/ -q
```

49 tests covering DCF correctness, sensitivity grid, archetype reachability, schemas, forward scenarios, session round-trip, SVG validity, exporter format, hard-exclusion compliance.

## Citations

- Modigliani, F., Miller, M. H. (1958). The Cost of Capital, Corporation Finance and the Theory of Investment. *American Economic Review*.
- Gordon, M. J. (1962). *The Investment, Financing, and Valuation of the Corporation*.
- Sharpe, W. F. (1964). Capital Asset Prices. *Journal of Finance*.
- Lintner, J. (1965). The Valuation of Risk Assets. *Review of Economics and Statistics*.
- Fama, E. F., French, K. R. (1993). Common risk factors. *Journal of Financial Economics*.
- Damodaran, A. (2002). *Investment Valuation*.
- Koller, T., Goedhart, M., Wessels, D. (2020). *Valuation: Measuring and Managing the Value of Companies* (McKinsey).
- Markowitz, H. (1952). Portfolio Selection. *Journal of Finance*.
- Black, F., Scholes, M. (1973). The Pricing of Options. *Journal of Political Economy*.
- Tversky, A., Kahneman, D. (1979). Prospect Theory. *Econometrica*.
- Bowlby, J. (1969). *Attachment and Loss*.

## License

MIT.

## Caveat

Half-serious tool using IB metaphors. **Not financial advice. Not relationship advice. Not therapy.** Conclusions describe how the inputs you supplied map onto IB valuation methodology — they say nothing definitive about real people or real relationships.
