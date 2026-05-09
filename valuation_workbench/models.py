"""Frozen dataclasses for the valuation pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class SchemaField:
    id: str
    label_zh: str
    label_en: str
    kind: str  # 'slider' | 'radio' | 'multi' | 'number'
    min: float = 0.0
    max: float = 10.0
    step: float = 1.0
    default: Any = 0
    options: tuple = ()           # for radio/multi: tuple of (value, label_zh, label_en)
    weight_e: float = 0.0          # weight in earnings (E)
    weight_bv: float = 0.0         # weight in book value (BV)
    weight_p: float = 0.0          # weight in price (P, your investment)
    weight_g: float = 0.0          # weight in growth (g)
    weight_vol: float = 0.0        # weight in volatility (β)
    forward_eligible: bool = False  # can be perturbed in scenarios

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Schema:
    target_type: str
    label_zh: str
    label_en: str
    description_zh: str
    description_en: str
    fields: tuple   # tuple of SchemaField

    def field_by_id(self, fid: str):
        for f in self.fields:
            if f.id == fid:
                return f
        return None

    def to_dict(self) -> dict:
        return {
            "target_type": self.target_type,
            "label_zh": self.label_zh,
            "label_en": self.label_en,
            "description_zh": self.description_zh,
            "description_en": self.description_en,
            "fields": [f.to_dict() for f in self.fields],
        }


@dataclass(frozen=True)
class Answers:
    target_type: str
    values: dict   # {field_id: numeric value}

    def to_dict(self) -> dict:
        return {"target_type": self.target_type, "values": dict(self.values)}


@dataclass(frozen=True)
class Scenario:
    name: str         # 'bear' | 'base' | 'bull'
    overrides: dict   # {field_id: override value}

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ValuationCore:
    E: float    # earnings per period
    BV: float   # book value
    P: float    # price (your investment)
    g: float    # growth rate
    beta: float
    wacc: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RatiosResult:
    pe: float
    pb: float
    eps: float
    pe_zh: str
    pe_en: str
    pb_zh: str
    pb_en: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DCFResult:
    five_year_pv: float
    terminal_value: float
    terminal_pv: float
    fair_value: float
    upside_pct: float    # (fair_value - P) / P
    wacc: float
    g: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SensitivityResult:
    g_grid: tuple
    wacc_grid: tuple
    table: tuple   # tuple of tuple of float (rows = g, cols = wacc)

    def to_dict(self) -> dict:
        return {
            "g_grid": list(self.g_grid),
            "wacc_grid": list(self.wacc_grid),
            "table": [list(r) for r in self.table],
        }


@dataclass(frozen=True)
class ArchetypeResult:
    archetype_id: str
    label_zh: str
    label_en: str
    description_zh: str
    description_en: str
    fit_score: float   # 0-1, how strongly the inputs match this archetype

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class StrategyResult:
    position: str         # LONG / SHORT / FLAT / HEDGE
    hold_period: str      # SHORT / MEDIUM / LONG / TERMINATE
    conviction: str       # STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
    rationale_zh: str
    rationale_en: str
    improvements_zh: tuple
    improvements_en: tuple

    def to_dict(self) -> dict:
        d = asdict(self)
        d["improvements_zh"] = list(self.improvements_zh)
        d["improvements_en"] = list(self.improvements_en)
        return d


@dataclass(frozen=True)
class ForensicsReport:
    target_type: str
    answers: dict
    core: ValuationCore
    ratios: RatiosResult
    dcf: DCFResult
    sensitivity: SensitivityResult
    archetype: ArchetypeResult
    strategy: StrategyResult
    scenarios: dict    # {'bear':..., 'base':..., 'bull':...}
    forward_var_name: str
    citations: tuple
    warnings: tuple
    version: str = "0.3.1"
    # Optional IB-grade extensions (set by run_pipeline_ib)
    ib_inputs: Any = None
    dcf3: Any = None
    multiples: Any = None
    asset: Any = None
    blended: Any = None
    mc: Any = None
    description: str = ""
    dyn_schema: Any = None

    def to_dict(self) -> dict:
        d = {
            "version": self.version,
            "target_type": self.target_type,
            "answers": self.answers,
            "core": self.core.to_dict(),
            "ratios": self.ratios.to_dict(),
            "dcf": self.dcf.to_dict(),
            "sensitivity": self.sensitivity.to_dict(),
            "archetype": self.archetype.to_dict(),
            "strategy": self.strategy.to_dict(),
            "scenarios": {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in self.scenarios.items()},
            "forward_var_name": self.forward_var_name,
            "citations": list(self.citations),
            "warnings": list(self.warnings),
            "description": self.description,
        }
        for k in ("ib_inputs", "dcf3", "multiples", "asset", "blended", "mc", "dyn_schema"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v.to_dict() if hasattr(v, "to_dict") else v
        return d


@dataclass(frozen=True)
class IBInputs:
    """Investment-banking-grade inputs after proxy → IB unit mapping."""
    fcf_base: float            # year-0 free cash flow
    growth_y1_3: float         # near-term growth rate (decimal)
    growth_y4_5: float         # mid-term growth rate (decimal)
    terminal_growth: float     # long-run growth (decimal)
    ebit_margin: float         # 0-1
    reinvestment_rate: float   # 0-1
    book_value: float
    comparable_pe: float
    comparable_pb: float
    comparable_ev_ebitda: float
    wacc_risk_premium: float   # extra risk premium added to base
    beta: float                # 0.3-2.5
    investment_cost: float     # P
    exit_cost: float
    red_flag_discount: float   # 0-0.5 multiplier
    moat: float                # 0-1
    risk_free: float = 0.04
    market_premium: float = 0.06

    @property
    def wacc(self) -> float:
        capm = self.risk_free + self.beta * self.market_premium
        w = capm + self.wacc_risk_premium
        floor = max(self.terminal_growth + 0.02, 0.05)
        return max(w, floor)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["wacc"] = self.wacc
        return d


@dataclass(frozen=True)
class DCF3StageResult:
    explicit_pv: float          # PV of years 1-5 (explicit)
    fade_pv: float              # PV of years 6-10 (linear fade to terminal_growth)
    terminal_value: float
    terminal_pv: float
    enterprise_value: float
    fair_value: float           # EV adjusted for red-flag discount
    upside_pct: float
    wacc: float
    yearly_fcf: tuple           # 10 yearly FCFs (pre-discount)
    yearly_pv: tuple            # 10 yearly discounted FCFs

    def to_dict(self) -> dict:
        d = asdict(self)
        d["yearly_fcf"] = list(self.yearly_fcf)
        d["yearly_pv"] = list(self.yearly_pv)
        return d


@dataclass(frozen=True)
class MultiplesResult:
    pe_implied: float
    pb_implied: float
    ev_ebitda_implied: float
    pe_value: float
    pb_value: float
    ev_ebitda_value: float
    blended: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AssetResult:
    book_floor: float           # liquidation floor
    replacement_cost: float
    value: float                # max(book, replacement)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BlendedValuation:
    dcf_value: float
    multiples_value: float
    asset_value: float
    weights: tuple              # (w_dcf, w_mult, w_asset)
    fair_low: float             # P10
    fair_mid: float             # P50 / weighted mean
    fair_high: float            # P90
    upside_pct: float
    pe_final: float
    pb_final: float
    eps: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["weights"] = list(self.weights)
        return d


@dataclass(frozen=True)
class MonteCarloResult:
    iters: int
    p10: float
    p50: float
    p90: float
    mean: float
    stdev: float
    prob_above_cost: float      # P(fair_value > investment_cost)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DynamicField:
    id: str
    label_zh: str
    label_en: str
    kind: str   # likert5/likert7/number/fillin/select/range
    hint_zh: str = ""
    hint_en: str = ""
    anchor_low_zh: str = ""    # e.g. "1=完全不主动"
    anchor_high_zh: str = ""   # e.g. "5=非常主动"
    min: float = 0.0
    max: float = 10.0
    step: float = 1.0
    default: Any = 0
    options: tuple = ()  # tuple of (value, label_zh, label_en)
    ib_param: str = ""
    scale: str = "linear"   # linear/inverse/log
    to_min: float = 0.0
    to_max: float = 1.0
    stage_id: str = ""
    sub_theme: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["options"] = [list(o) for o in self.options]
        return d


@dataclass(frozen=True)
class DynamicSubtheme:
    name_zh: str
    why_zh: str
    fields: tuple   # tuple of DynamicField

    def to_dict(self) -> dict:
        return {"name_zh": self.name_zh, "why_zh": self.why_zh,
                "fields": [f.to_dict() for f in self.fields]}


@dataclass(frozen=True)
class DynamicStage:
    id: str         # B1..B6
    label_zh: str
    why_matters_zh: str
    sub_themes: tuple   # tuple of DynamicSubtheme

    def to_dict(self) -> dict:
        return {"id": self.id, "label_zh": self.label_zh,
                "why_matters_zh": self.why_matters_zh,
                "sub_themes": [s.to_dict() for s in self.sub_themes]}

    @property
    def all_fields(self) -> tuple:
        out = []
        for s in self.sub_themes:
            out.extend(s.fields)
        return tuple(out)


@dataclass(frozen=True)
class DynamicSchema:
    title_zh: str
    title_en: str
    subtitle_zh: str
    subtitle_en: str
    subject_kind: str   # person/crush/relationship/self/other
    stages: tuple = ()      # tuple of DynamicStage (canonical 6-stage layout)
    fields: tuple = ()      # flat fields (used when an LLM emits a flat schema or by fixed-target flow)

    @property
    def all_fields(self) -> tuple:
        if self.stages:
            out = []
            for st in self.stages:
                out.extend(st.all_fields)
            return tuple(out)
        return self.fields

    def field_by_id(self, fid: str):
        for f in self.all_fields:
            if f.id == fid:
                return f
        return None

    def to_dict(self) -> dict:
        d = {
            "title_zh": self.title_zh, "title_en": self.title_en,
            "subtitle_zh": self.subtitle_zh, "subtitle_en": self.subtitle_en,
            "subject_kind": self.subject_kind,
        }
        if self.stages:
            d["stages"] = [s.to_dict() for s in self.stages]
        if self.fields:
            d["fields"] = [f.to_dict() for f in self.fields]
        return d


@dataclass
class Session:
    version: str = "0.3.1"
    saved_at: str = ""
    lang: str = "zh"
    stage: str = "A"   # A/B/C/D
    target_type: str = ""
    answers: dict = field(default_factory=dict)
    scenarios: dict = field(default_factory=lambda: {"bear": {}, "base": {}, "bull": {}})
    forward_var: dict = field(default_factory=dict)
    notes: str = ""
    description: str = ""           # Stage A free-text
    dyn_schema: dict = field(default_factory=dict)
    provider: str = ""
    model: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
