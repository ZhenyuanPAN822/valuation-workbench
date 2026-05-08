"""Tests for per-target schemas."""
from __future__ import annotations

from valuation_workbench import list_targets, get_schema
from valuation_workbench.models import Schema, SchemaField


def test_four_targets_present():
    targets = list_targets()
    assert set(targets) == {"person", "crush", "relationship", "self"}


def test_each_schema_has_min_fields():
    for t in list_targets():
        s = get_schema(t)
        assert len(s.fields) >= 8, f"target {t} has only {len(s.fields)} fields"


def test_field_types_valid():
    valid_kinds = {"slider", "radio", "multi", "number"}
    for t in list_targets():
        s = get_schema(t)
        for f in s.fields:
            assert f.kind in valid_kinds


def test_schema_to_dict_serializable():
    import json
    for t in list_targets():
        s = get_schema(t)
        json.dumps(s.to_dict())


def test_field_by_id():
    s = get_schema("crush")
    f = s.field_by_id("response_quality")
    assert f is not None
    f2 = s.field_by_id("nonexistent")
    assert f2 is None


def test_unknown_target():
    assert get_schema("nonexistent") is None
