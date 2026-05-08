"""Smoke test."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation_workbench import (
    list_targets, get_schema, run_pipeline,
    to_markdown, to_json,
    render_tear_sheet, render_sensitivity_heatmap, render_scenario_comparison,
    new_session, save_session, load_session,
)


def main():
    repo = Path(__file__).resolve().parents[1]
    out_dir = repo / "sample_outputs"
    out_dir.mkdir(exist_ok=True)
    summary = {}
    for t in list_targets():
        schema = get_schema(t)
        answers = {}
        for f in schema.fields:
            answers[f.id] = f.default if not isinstance(f.default, list) else []
        report = run_pipeline(t, answers)
        summary[t] = {
            "PE": round(report.ratios.pe, 2),
            "PB": round(report.ratios.pb, 2),
            "EPS": round(report.ratios.eps, 2),
            "FairValue": round(report.dcf.fair_value, 2),
            "Upside": round(report.dcf.upside_pct * 100, 1),
            "Archetype": report.archetype.archetype_id,
            "Position": report.strategy.position,
            "Conviction": report.strategy.conviction,
        }
        # render SVGs
        ts = render_tear_sheet(report)
        sh = render_sensitivity_heatmap(report)
        sc = render_scenario_comparison(report)
        for s in (ts, sh, sc):
            assert s.startswith("<svg") and s.endswith("</svg>"), t
        # write sample for first target
        if t == "crush":
            (out_dir / "sample-tear-sheet.svg").write_text(ts, encoding="utf-8")
            (out_dir / "sample-sensitivity.svg").write_text(sh, encoding="utf-8")
            (out_dir / "sample-scenarios.svg").write_text(sc, encoding="utf-8")
            (out_dir / "sample-report.md").write_text(to_markdown(report, lang="zh"), encoding="utf-8")
            (out_dir / "sample-report.json").write_text(to_json(report), encoding="utf-8")

    # Session roundtrip
    sess = new_session(lang="zh")
    sess.target_type = "crush"
    sess.answers = {"frequency_per_week": 7}
    sess.notes = "smoke test"
    payload = save_session(sess)
    sess2 = load_session(payload)
    assert sess2.notes == "smoke test"
    summary["session_roundtrip"] = "ok"

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
