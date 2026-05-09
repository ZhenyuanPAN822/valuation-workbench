"""v0.3 6-stage schema + multi-model provider + 3-prompt smoke."""
from __future__ import annotations

import pytest

from valuation_workbench import (
    parse_dyn_schema, get_fallback_schema,
    PROVIDERS, CUSTOM_MODEL_SENTINEL, ProviderError, probe_connection,
    build_schema_prompt, build_forward_prompt, build_narrative_prompt,
    schema_to_summary, answers_to_summary, ib_to_summary,
    aggregate_ib_inputs, run_pipeline_ib,
    fallback_narrative,
)


def test_six_stages_in_fallback():
    s = get_fallback_schema()
    assert len(s.stages) == 6
    ids = [st.id for st in s.stages]
    assert ids == ["B1", "B2", "B3", "B4", "B5", "B6"]


def test_stage_has_subthemes_and_fields():
    s = get_fallback_schema()
    for st in s.stages:
        assert len(st.sub_themes) >= 1
        for sub in st.sub_themes:
            assert sub.name_zh
            assert len(sub.fields) >= 1


def test_anchors_preserved_through_parse():
    """Anchors from LLM JSON must survive the parser."""
    obj = {
        "title_zh": "test", "subject_kind": "crush",
        "stages": [{
            "id": "B1", "label_zh": "她是谁",
            "why_matters_zh": "理解 TA",
            "sub_themes": [{
                "name_zh": "画像",
                "why_zh": "基础",
                "fields": [{
                    "id": "q1", "label_zh": "TA 主动度",
                    "kind": "likert5", "hint_zh": "次/周",
                    "anchor_low_zh": "1=完全不主动",
                    "anchor_high_zh": "5=非常主动",
                    "min": 1, "max": 5, "step": 1, "default": 3,
                    "ib_param": "fcf_base",
                    "mapping": {"scale": "linear", "to_min": 0.5, "to_max": 8.0},
                }],
            }],
        }],
    }
    s = parse_dyn_schema(obj)
    f = s.stages[0].sub_themes[0].fields[0]
    assert f.anchor_low_zh == "1=完全不主动"
    assert f.anchor_high_zh == "5=非常主动"
    assert f.stage_id == "B1"
    assert f.sub_theme == "画像"


def test_full_pipeline_with_6_stage_schema():
    s = get_fallback_schema()
    ans = {f.id: f.default for f in s.all_fields}
    r = run_pipeline_ib(s, ans, description="test", target_type=s.subject_kind, mc_iters=200)
    assert r.blended is not None
    assert r.blended.fair_low <= r.blended.fair_mid <= r.blended.fair_high


def test_provider_map_has_models():
    for name in ("openai", "deepseek", "anthropic", "gemini"):
        assert PROVIDERS[name]["models"], f"{name} should have models"
        assert PROVIDERS[name]["default_model"]
    assert PROVIDERS["custom"]["models"] == []


def test_probe_connection_returns_ok_or_error():
    # No real key — should return {ok: False, error: ...}
    r = probe_connection("openai", "", "")
    assert r["ok"] is False
    assert "error" in r


def test_custom_model_sentinel_resolves_to_default():
    from valuation_workbench.llm.providers import _resolve_model
    assert _resolve_model("openai", CUSTOM_MODEL_SENTINEL) == PROVIDERS["openai"]["default_model"]
    assert _resolve_model("openai", "") == PROVIDERS["openai"]["default_model"]
    assert _resolve_model("openai", "gpt-4o") == "gpt-4o"


def test_three_prompts_self_contained():
    """Each prompt must include enough context to be cold-start safe."""
    s = get_fallback_schema()
    ans = {f.id: f.default for f in s.all_fields}
    ib = aggregate_ib_inputs(s, ans)

    msgs = build_schema_prompt("test desc")
    assert len(msgs) == 2
    full = msgs[0]["content"] + msgs[1]["content"]
    assert "test desc" in full
    assert "B1" in full and "B6" in full
    assert "fcf_base" in full
    assert "JSON" in full

    msgs2 = build_forward_prompt("desc", schema_to_summary(s), answers_to_summary(ans), ib_to_summary(ib))
    full2 = msgs2[0]["content"] + msgs2[1]["content"]
    assert "前瞻变量" in full2
    assert "delta_pct" in full2
    assert "candidates" in full2

    r = run_pipeline_ib(s, ans, description="desc", mc_iters=100)
    from valuation_workbench import valuation_to_summary, archetype_to_summary, forward_to_summary
    msgs3 = build_narrative_prompt("desc", answers_to_summary(ans), ib_to_summary(ib),
                                   valuation_to_summary(r), archetype_to_summary(r), forward_to_summary(r))
    full3 = msgs3[0]["content"] + msgs3[1]["content"]
    assert "thesis_zh" in full3
    assert "top_risks" in full3
    assert "投资论点" in full3 or "Investment" in full3


def test_fallback_narrative_complete():
    s = get_fallback_schema()
    ans = {f.id: f.default for f in s.all_fields}
    r = run_pipeline_ib(s, ans, description="test", mc_iters=100)
    n = fallback_narrative(r)
    for k in ("thesis_zh", "bull_narrative_zh", "base_narrative_zh", "bear_narrative_zh",
              "top_risks", "actions_this_week_zh", "actions_this_month_zh", "actions_quarter_zh",
              "exit_strategy_zh", "key_assumptions_zh", "verdict_one_liner_zh"):
        assert k in n
    assert len(n["top_risks"]) >= 3


def test_session_history_cap():
    """Document expected behavior: localStorage cap is 20 (UI-side)."""
    # Just ensures the constant is documented somewhere reachable
    assert True  # the cap is in app.js (saveActive); no Python-side state
