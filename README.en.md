# Wall Street Valuation Workbench

English | [中文](README.zh-CN.md)

> Half-serious meme tool that runs **Wall Street IB-grade valuation** (DCF, P/E, P/B, EPS, sensitivity tables, forward-looking scenarios, archetype classification) on a person, a crush, a relationship, or yourself.

```bash
python app.py
# open http://127.0.0.1:8782
```

- **Pure Python stdlib** — zero runtime dependencies; one command to start.
- **Local-first** — all computation in your browser/machine; no upload, no telemetry.
- **Bilingual** — English + 中文 on the same code.
- **12+ canonical citations** — Modigliani-Miller, Gordon, Sharpe-Lintner, Damodaran, McKinsey *Valuation*, etc.
- **Session-resumable** — auto-save to localStorage; export/import as JSON.
- **Dynamic per-target form** — stages fixed (A/B/C/D), fields adapt per target type. Architecture inspired by [AI-decision-engine-zh](https://github.com/ZhenyuanPAN822/AI-decision-engine-zh).
- **Forward-looking variable** — IB-style "what if X happens" sensitivity, named.
- **Bloomberg-style tear sheet** — hero readouts, sensitivity heatmap, bear/base/bull comparison.

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
