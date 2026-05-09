"""Smoke test."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation_workbench import (
    list_targets, get_schema, run_pipeline, run_pipeline_ib,
    get_fallback_schema,
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

    # IB-grade pipeline smoke (fallback dynamic schema)
    dyn = get_fallback_schema()
    ib_ans = {f.id: f.default for f in dyn.fields}
    ib_report = run_pipeline_ib(dyn, ib_ans, description="smoke", target_type=dyn.subject_kind, mc_iters=200)
    assert ib_report.blended is not None
    assert ib_report.dcf3 is not None
    assert ib_report.mc is not None
    assert ib_report.blended.fair_low <= ib_report.blended.fair_mid <= ib_report.blended.fair_high
    summary["ib_pipeline"] = {
        "fair_low":  round(ib_report.blended.fair_low, 2),
        "fair_mid":  round(ib_report.blended.fair_mid, 2),
        "fair_high": round(ib_report.blended.fair_high, 2),
        "PE":        round(ib_report.blended.pe_final, 2),
        "PB":        round(ib_report.blended.pb_final, 2),
        "EPS":       round(ib_report.blended.eps, 2),
        "MC_P10":    round(ib_report.mc.p10, 2),
        "MC_P50":    round(ib_report.mc.p50, 2),
        "MC_P90":    round(ib_report.mc.p90, 2),
        "P_above_cost": round(ib_report.mc.prob_above_cost, 2),
        "archetype": ib_report.archetype.archetype_id,
        "wacc":      round(ib_report.ib_inputs.wacc, 4),
    }
    # Sample IB outputs
    (out_dir / "sample-ib-tear-sheet.svg").write_text(render_tear_sheet(ib_report), encoding="utf-8")
    (out_dir / "sample-ib-sensitivity.svg").write_text(render_sensitivity_heatmap(ib_report), encoding="utf-8")
    (out_dir / "sample-ib-scenarios.svg").write_text(render_scenario_comparison(ib_report), encoding="utf-8")
    (out_dir / "sample-ib-report.md").write_text(to_markdown(ib_report, lang="zh"), encoding="utf-8")
    (out_dir / "sample-ib-report.json").write_text(to_json(ib_report), encoding="utf-8")

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
