"""Server-side SVG charts for tear sheet, sensitivity heatmap, scenario comparison."""
from __future__ import annotations


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_tear_sheet(report) -> str:
    """A 'Bloomberg-style' tear-sheet header: 6 readouts + headline."""
    W, H = 720, 240
    bg = "#0b0e1f"
    fg = "#f5ecd9"
    amber = "#ffb454"
    teal = "#7ec4cf"
    rust = "#c44536"

    arch = report.archetype.label_zh
    pe = report.ratios.pe
    pb = report.ratios.pb
    eps = report.ratios.eps
    fv = report.dcf.fair_value
    upside = report.dcf.upside_pct * 100
    upside_color = teal if upside >= 0 else rust

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="{bg}"/>
<text x="20" y="32" font-family="Fraunces, Noto Serif SC, serif" font-style="italic" font-weight="500" font-size="22" fill="{fg}">{_esc(arch)} <tspan fill="{amber}">/</tspan> Valuation Tear Sheet</text>
<line x1="20" y1="48" x2="{W-20}" y2="48" stroke="{amber}" stroke-width="1" opacity="0.4"/>
<g font-family="JetBrains Mono, monospace" fill="{fg}">
<text x="20" y="80" font-size="11" fill="{amber}" letter-spacing="2">P/E</text>
<text x="20" y="118" font-size="32" font-family="Fraunces, serif" font-weight="500">{pe:.2f}</text>
<text x="140" y="80" font-size="11" fill="{amber}" letter-spacing="2">P/B</text>
<text x="140" y="118" font-size="32" font-family="Fraunces, serif" font-weight="500">{pb:.2f}</text>
<text x="260" y="80" font-size="11" fill="{amber}" letter-spacing="2">EPS</text>
<text x="260" y="118" font-size="32" font-family="Fraunces, serif" font-weight="500">{eps:.2f}</text>
<text x="380" y="80" font-size="11" fill="{amber}" letter-spacing="2">FAIR VALUE</text>
<text x="380" y="118" font-size="32" font-family="Fraunces, serif" font-weight="500">{fv:.1f}</text>
<text x="540" y="80" font-size="11" fill="{amber}" letter-spacing="2">UPSIDE</text>
<text x="540" y="118" font-size="32" font-family="Fraunces, serif" font-weight="500" fill="{upside_color}">{upside:+.1f}%</text>
</g>
<line x1="20" y1="148" x2="{W-20}" y2="148" stroke="{fg}" stroke-width="0.5" opacity="0.2"/>
<text x="20" y="178" font-family="JetBrains Mono, monospace" font-size="11" fill="{teal}" letter-spacing="2">POSITION · HOLD · CONVICTION</text>
<text x="20" y="210" font-family="Fraunces, Noto Serif SC, serif" font-style="italic" font-size="20" fill="{fg}">{_esc(report.strategy.position)} · {_esc(report.strategy.hold_period)} · <tspan fill="{amber}">{_esc(report.strategy.conviction)}</tspan></text>
</svg>"""


def render_sensitivity_heatmap(report) -> str:
    """5×5 heatmap of DCF sensitivity (g × WACC)."""
    s = report.sensitivity
    W, H = 540, 320
    cell_w = (W - 100) / max(len(s.wacc_grid), 1)
    cell_h = (H - 80) / max(len(s.g_grid), 1)
    bg = "#fef3c7"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="{bg}"/>']
    parts.append(f'<text x="14" y="22" font-family="serif" font-size="14" fill="#1f2937">敏感性分析: g × WACC → fair value</text>')

    flat = [v for row in s.table for v in row]
    if flat:
        vmin, vmax = min(flat), max(flat)
    else:
        vmin, vmax = 0, 1

    for i, g in enumerate(s.g_grid):
        for j, wacc in enumerate(s.wacc_grid):
            v = s.table[i][j]
            ratio = (v - vmin) / max(vmax - vmin, 0.0001)
            r = int(217 + (22 - 217) * ratio)   # ochre to teal
            g_c = int(119 + (148 - 119) * ratio)
            b = int(6 + (199 - 6) * ratio)
            color = f"rgb({r},{g_c},{b})"
            x = 60 + j * cell_w
            y = 50 + i * cell_h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w-1:.1f}" height="{cell_h-1:.1f}" fill="{color}"/>')
            parts.append(f'<text x="{x+cell_w/2:.1f}" y="{y+cell_h/2+4:.1f}" font-size="10" font-family="monospace" fill="#fff" text-anchor="middle">{v:.0f}</text>')

    # row labels (g)
    for i, g in enumerate(s.g_grid):
        parts.append(f'<text x="50" y="{50 + i*cell_h + cell_h/2 + 4:.1f}" font-size="10" fill="#1f2937" text-anchor="end">{g*100:+.0f}%</text>')
    # col labels (wacc)
    for j, wacc in enumerate(s.wacc_grid):
        parts.append(f'<text x="{60 + j*cell_w + cell_w/2:.1f}" y="48" font-size="10" fill="#1f2937" text-anchor="middle">{wacc*100:.0f}%</text>')

    parts.append('</svg>')
    return "".join(parts)


def render_scenario_comparison(report) -> str:
    """Bar chart comparing bear / base / bull DCF."""
    W, H = 540, 240
    bg = "#ecfeff"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="{bg}"/>']
    parts.append(f'<text x="14" y="22" font-family="serif" font-size="14" fill="#1f2937">Bear / Base / Bull 三场景对比 (E vs g vs wacc)</text>')

    scenarios = report.scenarios
    names = ["bear", "base", "bull"]
    pad = 60
    bar_w = (W - 2*pad) / (len(names) * 3 + (len(names) - 1))
    metrics = [("E", "#d97706"), ("g", "#0e7490"), ("wacc", "#c44536")]

    # find max for scaling
    all_vals = []
    for n in names:
        sc = scenarios.get(n, {})
        for m, _ in metrics:
            try:
                all_vals.append(float(sc.get(m, 0)))
            except (TypeError, ValueError):
                pass
    vmax = max(all_vals) if all_vals else 1.0

    for ni, n in enumerate(names):
        sc = scenarios.get(n, {})
        x_base = pad + ni * (3 * bar_w + bar_w)
        for mi, (m, c) in enumerate(metrics):
            try:
                v = float(sc.get(m, 0))
            except (TypeError, ValueError):
                v = 0
            h = (H - 80) * (v / max(vmax, 0.01))
            x = x_base + mi * bar_w
            y = H - 40 - h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w-2:.1f}" height="{h:.1f}" fill="{c}"/>')
        parts.append(f'<text x="{x_base + 1.5*bar_w:.1f}" y="{H-15}" font-size="11" fill="#1f2937" text-anchor="middle">{n}</text>')

    # legend
    for mi, (m, c) in enumerate(metrics):
        parts.append(f'<rect x="{W - 200 + mi*60}" y="40" width="12" height="12" fill="{c}"/>')
        parts.append(f'<text x="{W - 184 + mi*60}" y="50" font-size="10" fill="#1f2937">{m}</text>')

    parts.append('</svg>')
    return "".join(parts)
