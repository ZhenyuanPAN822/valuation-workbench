"""Tests for valuation core (E/BV/P aggregation)."""
from __future__ import annotations

from valuation_workbench import get_schema
from valuation_workbench.models import Answers
from valuation_workbench.valuation.core import compute_core


def test_compute_core_returns_finite():
    schema = get_schema("crush")
    answers = Answers(target_type="crush", values={f.id: f.default if not isinstance(f.default, list) else [] for f in schema.fields})
    c = compute_core(schema, answers)
    import math
    for v in (c.E, c.BV, c.P, c.g, c.beta, c.wacc):
        assert math.isfinite(v)


def test_wacc_above_g():
    """WACC must be > g."""
    schema = get_schema("self")
    answers = Answers(target_type="self", values={f.id: f.max for f in schema.fields if f.kind == "slider"})
    c = compute_core(schema, answers)
    assert c.wacc > c.g


def test_high_investment_high_p():
    """Higher slider values on weight_p fields → higher P."""
    schema = get_schema("crush")
    low = Answers(target_type="crush", values={"your_weekly_hours": 1, "frequency_per_week": 1, "relationship_age_months": 1, "effort_balance": 5})
    high = Answers(target_type="crush", values={"your_weekly_hours": 30, "frequency_per_week": 14, "relationship_age_months": 36, "effort_balance": 5})
    cl = compute_core(schema, low)
    ch = compute_core(schema, high)
    assert ch.P > cl.P


def test_higher_quality_higher_e():
    schema = get_schema("crush")
    low = Answers(target_type="crush", values={"response_quality": 1})
    high = Answers(target_type="crush", values={"response_quality": 10})
    cl = compute_core(schema, low)
    ch = compute_core(schema, high)
    assert ch.E > cl.E
