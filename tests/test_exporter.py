"""Tests for Markdown / JSON export."""
from __future__ import annotations

import json
from valuation_workbench import run_pipeline, get_schema, to_markdown, to_json


def _r(target):
    s = get_schema(target)
    ans = {f.id: f.default if not isinstance(f.default, list) else [] for f in s.fields}
    return run_pipeline(target, ans)


def test_markdown_zh_has_sections():
    md = to_markdown(_r("crush"), lang="zh")
    assert "估值报告" in md
    assert "DCF" in md
    assert "敏感性" in md


def test_markdown_en_has_sections():
    md = to_markdown(_r("crush"), lang="en")
    assert "Tear Sheet" in md
    assert "Strategy" in md


def test_json_serializable():
    js = to_json(_r("self"))
    parsed = json.loads(js)
    assert parsed["version"] == "0.3.1"
    assert "core" in parsed and "ratios" in parsed and "dcf" in parsed


def test_disclaimer_present():
    md = to_markdown(_r("crush"), lang="zh")
    assert "非心理咨询" in md or "非财务" in md
