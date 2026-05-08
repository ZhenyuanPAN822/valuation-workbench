"""Tests for SVG renderers."""
from __future__ import annotations

from valuation_workbench import (
    run_pipeline, get_schema,
    render_tear_sheet, render_sensitivity_heatmap, render_scenario_comparison,
)


def _r():
    s = get_schema("crush")
    ans = {f.id: f.default if not isinstance(f.default, list) else [] for f in s.fields}
    return run_pipeline("crush", ans)


def test_tear_sheet_valid_svg():
    svg = render_tear_sheet(_r())
    assert svg.startswith("<svg") and svg.endswith("</svg>")


def test_sensitivity_heatmap_valid_svg():
    svg = render_sensitivity_heatmap(_r())
    assert svg.startswith("<svg") and svg.endswith("</svg>")


def test_scenarios_valid_svg():
    svg = render_scenario_comparison(_r())
    assert svg.startswith("<svg") and svg.endswith("</svg>")
