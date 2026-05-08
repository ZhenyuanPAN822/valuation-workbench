"""Schema for 自己 (self) valuation."""
from ..models import SchemaField, Schema


SELF_SCHEMA = Schema(
    target_type="self",
    label_zh="给自己做估值",
    label_en="Self Valuation",
    description_zh="把'我现在值多少'翻译成 IB 估值表。EPS / PE / DCF / forward optionality 全套。",
    description_en="Translate 'what am I worth' into IB valuation. Full ratios + DCF + forward optionality.",
    fields=(
        SchemaField(
            id="skill_quality",
            label_zh="技能质量 (1-10)",
            label_en="Skill quality",
            kind="slider", min=1, max=10, step=1, default=6,
            weight_e=1.5, weight_bv=1.0,
        ),
        SchemaField(
            id="network_quality",
            label_zh="人脉质量 (1-10)",
            label_en="Network quality",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_bv=1.2,
        ),
        SchemaField(
            id="savings_runway_months",
            label_zh="存款 runway (月)",
            label_en="Savings runway (months)",
            kind="slider", min=0, max=60, step=1, default=6,
            weight_bv=0.5, weight_vol=-0.4,
        ),
        SchemaField(
            id="earning_growth_rate_pct",
            label_zh="收入年增长率 (%)",
            label_en="Earning growth rate (%)",
            kind="slider", min=0, max=50, step=1, default=5,
            weight_g=2.0,
            forward_eligible=True,
        ),
        SchemaField(
            id="health_score",
            label_zh="身心健康 (1-10)",
            label_en="Health score",
            kind="slider", min=1, max=10, step=1, default=7,
            weight_e=0.8, weight_vol=-0.5,
        ),
        SchemaField(
            id="relationship_score",
            label_zh="情感关系状态 (1-10)",
            label_en="Relationship score",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_e=0.5, weight_bv=0.3,
        ),
        SchemaField(
            id="meaningful_projects_count",
            label_zh="有意义项目数",
            label_en="Meaningful projects count",
            kind="slider", min=0, max=10, step=1, default=2,
            weight_e=0.8,
        ),
        SchemaField(
            id="forward_optionality",
            label_zh="前瞻可选性 (1-10)",
            label_en="Forward optionality",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_g=1.0, weight_bv=0.5,
            forward_eligible=True,
        ),
        SchemaField(
            id="regret_index",
            label_zh="遗憾指数 (1-10)",
            label_en="Regret index",
            kind="slider", min=1, max=10, step=1, default=4,
            weight_p=0.8, weight_vol=0.3,
        ),
    ),
)
