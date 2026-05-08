"""Tests for session save/load."""
from __future__ import annotations

import json
import pytest

from valuation_workbench import new_session, save_session, load_session


def test_new_session_default():
    s = new_session()
    assert s.version == "0.1.0"
    assert s.lang == "zh"
    assert s.stage == "A"


def test_save_load_roundtrip():
    s = new_session()
    s.target_type = "crush"
    s.answers = {"response_quality": 7}
    s.notes = "test"
    payload = save_session(s)
    s2 = load_session(payload)
    assert s2.target_type == "crush"
    assert s2.answers == {"response_quality": 7}


def test_load_invalid_json():
    with pytest.raises(ValueError):
        load_session("not json")


def test_load_partial_session():
    payload = json.dumps({"version": "0.1.0", "tabs_or_whatever": {}})
    s = load_session(payload)
    assert s.target_type == ""
    assert s.answers == {}
