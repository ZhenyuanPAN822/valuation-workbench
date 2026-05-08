"""Schema for 人 (general person) valuation."""
from ..models import SchemaField, Schema


PERSON_SCHEMA = Schema(
    target_type="person",
    label_zh="给一个人做估值",
    label_en="Person Valuation",
    description_zh="给任何一个人(朋友, 同事, 合作伙伴, 介绍对象)做 IB 级估值。",
    description_en="IB-grade valuation for any person — friend, coworker, partner, introduction.",
    fields=(
        SchemaField(
            id="known_duration_months",
            label_zh="认识时长(月)",
            label_en="Known duration (months)",
            kind="slider", min=0, max=120, step=1, default=12,
            weight_bv=1.0, weight_p=0.4,  # accumulated time = capital invested
        ),
        SchemaField(
            id="shared_history_quality",
            label_zh="共同经历质量 (1-10)",
            label_en="Shared history quality",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_e=0.8, weight_bv=0.8,
        ),
        SchemaField(
            id="reliability",
            label_zh="可靠度 (1-10)",
            label_en="Reliability",
            kind="slider", min=1, max=10, step=1, default=6,
            weight_e=1.2, weight_vol=-0.5,
        ),
        SchemaField(
            id="competence",
            label_zh="能力 (1-10)",
            label_en="Competence",
            kind="slider", min=1, max=10, step=1, default=6,
            weight_e=1.0, weight_g=0.8,
        ),
        SchemaField(
            id="character_signals",
            label_zh="品格信号(多选)",
            label_en="Character signals",
            kind="multi", default=[],
            options=(
                ("punctual", "守时", "punctual"),
                ("trustworthy", "守信", "trustworthy"),
                ("accountable", "担当", "accountable"),
                ("empathic", "同理心", "empathic"),
                ("boundaries", "边界感", "boundaries"),
                ("self_driven", "自驱力", "self-driven"),
                ("resilient", "韧性", "resilient"),
            ),
            weight_e=0.5, weight_bv=0.5,
        ),
        SchemaField(
            id="network_value",
            label_zh="圈子价值 (1-10)",
            label_en="Network value",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_bv=1.0,
        ),
        SchemaField(
            id="potential_growth",
            label_zh="潜力 (1-10)",
            label_en="Growth potential",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_g=1.5,
            forward_eligible=True,
        ),
        SchemaField(
            id="red_flags_count",
            label_zh="红旗数量 (0-10)",
            label_en="Red flags count",
            kind="slider", min=0, max=10, step=1, default=1,
            weight_vol=1.5, weight_e=-0.5, weight_p=0.6,  # red flags increase implicit cost
        ),
        SchemaField(
            id="your_alternative_quality",
            label_zh="你的备选质量 (1-10)",
            label_en="Your alternatives quality",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_vol=-0.3,
        ),
    ),
)
