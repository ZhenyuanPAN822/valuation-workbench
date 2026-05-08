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
    version: str = "0.1.0"

    def to_dict(self) -> dict:
        return {
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
        }


@dataclass
class Session:
    version: str = "0.1.0"
    saved_at: str = ""
    lang: str = "zh"
    stage: str = "A"   # A/B/C/D
    target_type: str = ""
    answers: dict = field(default_factory=dict)
    scenarios: dict = field(default_factory=lambda: {"bear": {}, "base": {}, "bull": {}})
    forward_var: dict = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
