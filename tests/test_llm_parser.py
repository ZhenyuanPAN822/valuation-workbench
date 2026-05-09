"""Three-tier JSON parser + dynamic-schema validator + provider error dispatch."""
from __future__ import annotations

import pytest

from valuation_workbench import (
    parse_llm_json, ParseError,
    parse_dyn_schema, get_fallback_schema,
    call_llm, ProviderError,
)


def test_direct_parse():
    obj = parse_llm_json('{"a": 1, "b": [2, 3]}')
    assert obj == {"a": 1, "b": [2, 3]}


def test_fenced_json_block():
    raw = '''Here is the schema:
```json
{"title_zh": "x", "fields": []}
```
Hope this helps!'''
    obj = parse_llm_json(raw)
    assert obj["title_zh"] == "x"


def test_brace_slice_fallback():
    raw = 'Sure! {"k": "v", "n": 42} done'
    obj = parse_llm_json(raw)
    assert obj == {"k": "v", "n": 42}


def test_empty_raises():
    with pytest.raises(ParseError):
        parse_llm_json("")


def test_garbage_raises():
    with pytest.raises(ParseError):
        parse_llm_json("nothing useful here")


def test_dyn_schema_accepts_fields_alias_questions():
    obj = {
        "title": "test",
        "subject_kind": "crush",
        "questions": [
            {"id": "q1", "question_zh": "你愿意每周见几次?", "kind": "number",
             "min": 0, "max": 7, "step": 1, "default": 2,
             "ib_param": "fcf_base", "mapping": {"scale": "linear", "to_min": 0.5, "to_max": 8.0}},
        ],
    }
    s = parse_dyn_schema(obj)
    assert s.subject_kind == "crush"
    assert len(s.fields) == 1
    assert s.fields[0].ib_param == "fcf_base"
    assert s.fields[0].label_zh.startswith("你愿意")


def test_dyn_schema_drops_invalid_kind_to_default():
    obj = {"fields": [{"id": "x", "kind": "supercrazy", "label_zh": "?"}]}
    s = parse_dyn_schema(obj)
    assert s.fields[0].kind == "likert5"


def test_dyn_schema_strips_unknown_ib_param():
    obj = {"fields": [{"id": "x", "kind": "likert5", "label_zh": "?", "ib_param": "made_up_thing"}]}
    s = parse_dyn_schema(obj)
    assert s.fields[0].ib_param == ""


def test_fallback_schema_self_consistent():
    s = get_fallback_schema()
    assert len(s.all_fields) >= 8
    assert len(s.stages) == 6
    ib_params = {f.ib_param for f in s.all_fields if f.ib_param}
    # Must cover at least 4 IB-param classes
    classes = {
        "value": {"fcf_base", "ebit_margin", "reinvestment_rate"},
        "growth": {"revenue_growth_y1_3", "revenue_growth_y4_5", "terminal_growth"},
        "risk": {"beta_proxy", "wacc_risk_premium", "red_flags"},
        "asset": {"investment_cost", "book_value", "moat", "exit_cost"},
    }
    for name, group in classes.items():
        assert ib_params & group, f"fallback missing {name} class"


def test_call_llm_requires_provider():
    with pytest.raises(ProviderError):
        call_llm("", "k", "m", [{"role": "user", "content": "hi"}])


def test_call_llm_requires_key():
    with pytest.raises(ProviderError):
        call_llm("openai", "", "m", [{"role": "user", "content": "hi"}])


def test_call_llm_unknown_provider():
    with pytest.raises(ProviderError):
        call_llm("megacorp", "k", "m", [{"role": "user", "content": "hi"}])


def test_call_llm_custom_requires_endpoint():
    with pytest.raises(ProviderError):
        call_llm("custom", "k", "m", [{"role": "user", "content": "hi"}])
