"""Forward-looking variable + 3-scenario pipeline.

Two pipelines coexist:
  run_pipeline       — legacy (4-card hardcoded Schema)
  run_pipeline_ib    — IB-grade (LLM-generated DynamicSchema + IB engine)
"""
from __future__ import annotations

from .models import (
    Answers, Schema,
    ValuationCore, RatiosResult, DCFResult, SensitivityResult,
    DynamicSchema, IBInputs, BlendedValuation, ForensicsReport,
)
from .schemas import get_schema
from .valuation.core import compute_core
from .valuation.ratios import compute_ratios
from .valuation.dcf import compute_dcf, sensitivity_table
from .valuation.archetype import classify, classify_ib
from .valuation.strategy import recommend
from .valuation.ib_engine import (
    aggregate_ib_inputs, compute_dcf_3stage, compute_multiples,
    compute_asset, blend_valuations, monte_carlo,
)


# ───────────────────────── Legacy pipeline (kept for tests/back-compat) ─────────────────────────

def build_scenarios(schema: Schema, base_answers: Answers, forward_var_id: str = "", delta_pct: float = 0.30) -> dict:
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
        core=core, ratios=ratios, dcf=dcf, sensitivity=sens,
        archetype=archetype, strategy=strategy,
        scenarios=scenarios_serializable,
        forward_var_name=forward_var_name or forward_var_id,
        citations=CITATIONS,
        warnings=tuple(warnings),
    )


# ───────────────────────── IB-grade pipeline ─────────────────────────

def _ib_to_legacy_core(ib: IBInputs, blended: BlendedValuation) -> ValuationCore:
    return ValuationCore(
        E=blended.eps,
        BV=ib.book_value,
        P=ib.investment_cost,
        g=ib.growth_y1_3,
        beta=ib.beta,
        wacc=ib.wacc,
    )


def _ib_to_legacy_dcf(ib: IBInputs, dcf3, blended: BlendedValuation) -> DCFResult:
    return DCFResult(
        five_year_pv=dcf3.explicit_pv,
        terminal_value=dcf3.terminal_value,
        terminal_pv=dcf3.terminal_pv,
        fair_value=blended.fair_mid,
        upside_pct=blended.upside_pct,
        wacc=dcf3.wacc,
        g=ib.growth_y1_3,
    )


def _ib_to_legacy_ratios(blended: BlendedValuation) -> RatiosResult:
    pe = blended.pe_final
    pb = blended.pb_final
    if pe < 8:
        pe_zh = f"P/E = {pe:.2f} → 低估区"
        pe_en = f"P/E = {pe:.2f} → undervalued"
    elif pe < 18:
        pe_zh = f"P/E = {pe:.2f} → 合理估值"
        pe_en = f"P/E = {pe:.2f} → fairly valued"
    elif pe < 35:
        pe_zh = f"P/E = {pe:.2f} → 偏高 (溢价)"
        pe_en = f"P/E = {pe:.2f} → premium"
    else:
        pe_zh = f"P/E = {pe:.2f} → 极度高估"
        pe_en = f"P/E = {pe:.2f} → extreme premium"
    if pb < 0.7:
        pb_zh = f"P/B = {pb:.2f} → 折价"
        pb_en = f"P/B = {pb:.2f} → below book"
    elif pb < 2.0:
        pb_zh = f"P/B = {pb:.2f} → 接近账面"
        pb_en = f"P/B = {pb:.2f} → near book"
    elif pb < 4.0:
        pb_zh = f"P/B = {pb:.2f} → 溢价"
        pb_en = f"P/B = {pb:.2f} → premium"
    else:
        pb_zh = f"P/B = {pb:.2f} → 极度溢价"
        pb_en = f"P/B = {pb:.2f} → extreme premium"
    return RatiosResult(
        pe=pe, pb=pb, eps=blended.eps,
        pe_zh=pe_zh, pe_en=pe_en, pb_zh=pb_zh, pb_en=pb_en,
    )


def _sensitivity_from_ib(ib: IBInputs, archetype_id: str) -> SensitivityResult:
    """7×7 sensitivity table on (terminal_growth × wacc_risk_premium)."""
    g_grid = tuple(round(ib.terminal_growth + d, 4) for d in (-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03))
    rp_grid = tuple(round(max(ib.wacc_risk_premium + d, 0.0), 4) for d in (-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03))
    rows = []
    for gt in g_grid:
        row = []
        for rp in rp_grid:
            ib_p = IBInputs(**{**ib.to_dict(), "terminal_growth": gt, "wacc_risk_premium": rp,
                                "wacc": None}) if False else IBInputs(
                fcf_base=ib.fcf_base, growth_y1_3=ib.growth_y1_3, growth_y4_5=ib.growth_y4_5,
                terminal_growth=gt, ebit_margin=ib.ebit_margin, reinvestment_rate=ib.reinvestment_rate,
                book_value=ib.book_value, comparable_pe=ib.comparable_pe, comparable_pb=ib.comparable_pb,
                comparable_ev_ebitda=ib.comparable_ev_ebitda, wacc_risk_premium=rp, beta=ib.beta,
                investment_cost=ib.investment_cost, exit_cost=ib.exit_cost,
                red_flag_discount=ib.red_flag_discount, moat=ib.moat,
            )
            d3 = compute_dcf_3stage(ib_p)
            mu = compute_multiples(ib_p)
            asv = compute_asset(ib_p)
            bl = blend_valuations(ib_p, d3, mu, asv, archetype_id)
            row.append(round(bl.fair_mid, 2))
        rows.append(tuple(row))
    return SensitivityResult(g_grid=g_grid, wacc_grid=rp_grid, table=tuple(rows))


def build_scenarios_ib(schema: DynamicSchema, base_answers: dict, forward_var_id: str = "", delta_pct: float = 0.30) -> dict:
    """Perturb forward_var_id (or all numeric fields, lightly) → bear/base/bull IBInputs."""
    ib_base = aggregate_ib_inputs(schema, base_answers)

    all_fields = schema.all_fields if hasattr(schema, "all_fields") else schema.fields

    def perturb(factor: float) -> IBInputs:
        new_values = dict(base_answers)
        target_ids = [forward_var_id] if forward_var_id else [f.id for f in all_fields if f.kind in ("likert5","likert7","number","range")]
        for fid in target_ids:
            f = next((x for x in all_fields if x.id == fid), None)
            if not f:
                continue
            cur = new_values.get(fid, f.default)
            try:
                cur_f = float(cur)
            except (TypeError, ValueError):
                continue
            shifted = cur_f * (1 + factor)
            shifted = max(f.min, min(f.max, shifted))
            new_values[fid] = shifted
        return aggregate_ib_inputs(schema, new_values)

    return {"bear": perturb(-delta_pct), "base": ib_base, "bull": perturb(+delta_pct)}


def run_pipeline_ib(
    dyn_schema: DynamicSchema,
    answers_values: dict,
    description: str = "",
    forward_var_id: str = "",
    forward_var_name: str = "",
    delta_pct: float = 0.30,
    target_type: str = "",
    mc_iters: int = 800,
) -> ForensicsReport:
    """Full IB pipeline: dyn_schema + answers → 3-stage DCF + multiples + asset + blend + MC."""
    ib = aggregate_ib_inputs(dyn_schema, answers_values)
    dcf3 = compute_dcf_3stage(ib)
    mult = compute_multiples(ib)
    asset = compute_asset(ib)
    blended_tmp = blend_valuations(ib, dcf3, mult, asset, "default")
    archetype = classify_ib(ib, blended_tmp)
    blended = blend_valuations(ib, dcf3, mult, asset, archetype.archetype_id)
    mc = monte_carlo(ib, archetype.archetype_id, iters=mc_iters)

    legacy_core = _ib_to_legacy_core(ib, blended)
    legacy_dcf = _ib_to_legacy_dcf(ib, dcf3, blended)
    legacy_ratios = _ib_to_legacy_ratios(blended)
    sens = _sensitivity_from_ib(ib, archetype.archetype_id)

    strategy = recommend(legacy_core, legacy_ratios, legacy_dcf, archetype, target_type or dyn_schema.subject_kind)

    scenarios_ib = build_scenarios_ib(dyn_schema, answers_values, forward_var_id, delta_pct)
    scenarios_serializable = {}
    for name, ib_s in scenarios_ib.items():
        d3_s = compute_dcf_3stage(ib_s)
        mu_s = compute_multiples(ib_s)
        as_s = compute_asset(ib_s)
        bl_s = blend_valuations(ib_s, d3_s, mu_s, as_s, archetype.archetype_id)
        scenarios_serializable[name] = {
            "E": bl_s.eps, "BV": ib_s.book_value, "P": ib_s.investment_cost,
            "g": ib_s.growth_y1_3, "beta": ib_s.beta, "wacc": ib_s.wacc,
            "fair_mid": bl_s.fair_mid, "upside_pct": bl_s.upside_pct,
        }

    from . import CITATIONS

    warnings = []
    if ib.wacc - ib.terminal_growth < 0.02:
        warnings.append("WACC 接近 terminal_growth; 已应用安全护栏")
    if mc.stdev / max(mc.mean, 0.01) > 0.6:
        warnings.append(f"蒙卡变异系数 {mc.stdev/max(mc.mean,0.01)*100:.0f}% — 估值不确定性高")
    if ib.red_flag_discount > 0.20:
        warnings.append(f"Red-flag 折扣 {ib.red_flag_discount*100:.0f}% — 重大风险")

    return ForensicsReport(
        target_type=target_type or dyn_schema.subject_kind,
        answers=dict(answers_values),
        core=legacy_core, ratios=legacy_ratios, dcf=legacy_dcf, sensitivity=sens,
        archetype=archetype, strategy=strategy,
        scenarios=scenarios_serializable,
        forward_var_name=forward_var_name or forward_var_id,
        citations=CITATIONS,
        warnings=tuple(warnings),
        ib_inputs=ib, dcf3=dcf3, multiples=mult, asset=asset, blended=blended, mc=mc,
        description=description,
        dyn_schema=dyn_schema,
    )
