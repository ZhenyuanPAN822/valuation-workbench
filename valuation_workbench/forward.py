"""Forward-looking variable + 3-scenario (bear / base / bull) pipeline."""
from __future__ import annotations

from .models import (
    Answers, Schema, Scenario,
    ValuationCore, ForensicsReport,
)
from .schemas import get_schema
from .valuation.core import compute_core
from .valuation.ratios import compute_ratios
from .valuation.dcf import compute_dcf, sensitivity_table
from .valuation.archetype import classify
from .valuation.strategy import recommend


def build_scenarios(schema: Schema, base_answers: Answers, forward_var_id: str = "", delta_pct: float = 0.30) -> dict:
    """Build bear / base / bull scenarios by perturbing forward_var_id (or all forward_eligible).

    Returns: {'bear': ValuationCore, 'base': ValuationCore, 'bull': ValuationCore}
    """
    forward_ids = []
    if forward_var_id:
        f = schema.field_by_id(forward_var_id)
        if f and f.forward_eligible:
            forward_ids = [forward_var_id]
    if not forward_ids:
        forward_ids = [f.id for f in schema.fields if f.forward_eligible]

    base_core = compute_core(schema, base_answers)

    def perturb(values, factor):
        new_values = dict(values)
        for fid in forward_ids:
            field = schema.field_by_id(fid)
            if not field:
                continue
            cur = new_values.get(fid, field.default)
            try:
                cur_f = float(cur)
            except (TypeError, ValueError):
                continue
            shifted = cur_f * (1 + factor)
            shifted = max(field.min, min(field.max, shifted))
            new_values[fid] = shifted
        return Answers(target_type=schema.target_type, values=new_values)

    bear_ans = perturb(base_answers.values, -delta_pct)
    bull_ans = perturb(base_answers.values, +delta_pct)

    return {
        "bear": compute_core(schema, bear_ans),
        "base": base_core,
        "bull": compute_core(schema, bull_ans),
    }


def run_pipeline(target_type: str, answers_values: dict, forward_var_id: str = "", forward_var_name: str = "", delta_pct: float = 0.30) -> ForensicsReport:
    """Full pipeline: schema → core → ratios → dcf → sensitivity → archetype → strategy."""
    schema = get_schema(target_type)
    if not schema:
        raise ValueError(f"unknown target_type: {target_type}")
    answers = Answers(target_type=target_type, values=answers_values)
    core = compute_core(schema, answers)
    ratios = compute_ratios(core)
    dcf = compute_dcf(core)
    sens = sensitivity_table(core)
    archetype = classify(core, ratios.pe, ratios.pb, dcf.upside_pct)
    strategy = recommend(core, ratios, dcf, archetype, target_type)
    scenarios = build_scenarios(schema, answers, forward_var_id, delta_pct)
    # convert ValuationCore objects to dicts in scenarios
    scenarios_serializable = {k: v.to_dict() if hasattr(v, 'to_dict') else v for k, v in scenarios.items()}

    from . import CITATIONS

    warnings = []
    if core.wacc - core.g < 0.02:
        warnings.append("WACC 接近 g, terminal value 不稳定; 已应用安全护栏")
    if abs(dcf.upside_pct) > 5.0:
        warnings.append("DCF 上行/下行空间极端, 请重新校核输入")

    return ForensicsReport(
        target_type=target_type,
        answers=answers.values,
        core=core,
        ratios=ratios,
        dcf=dcf,
        sensitivity=sens,
        archetype=archetype,
        strategy=strategy,
        scenarios=scenarios_serializable,
        forward_var_name=forward_var_name or forward_var_id,
        citations=CITATIONS,
        warnings=tuple(warnings),
    )
