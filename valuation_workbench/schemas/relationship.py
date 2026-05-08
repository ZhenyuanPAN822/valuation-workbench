"""Schema for 一段感情 (relationship) valuation."""
from ..models import SchemaField, Schema


RELATIONSHIP_SCHEMA = Schema(
    target_type="relationship",
    label_zh="给一段感情做估值",
    label_en="Relationship Valuation",
    description_zh="把'要不要继续这段感情'翻译成 IB 估值。考虑维护成本、退出成本、增长对齐等。",
    description_en="Translate 'should I stay in this relationship' into IB valuation, accounting for maintenance/exit costs, growth alignment.",
    fields=(
        SchemaField(
            id="relationship_age_years",
            label_zh="关系时长(年)",
            label_en="Duration (years)",
            kind="slider", min=0, max=10, step=0.5, default=1,
            weight_bv=1.5, weight_p=0.5,
        ),
        SchemaField(
            id="conflict_frequency",
            label_zh="冲突频率 (1-10)",
            label_en="Conflict frequency",
            kind="slider", min=1, max=10, step=1, default=4,
            weight_p=0.8, weight_vol=1.5,
        ),
        SchemaField(
            id="repair_quality",
            label_zh="修复质量 (1-10)",
            label_en="Repair quality (after conflict)",
            kind="slider", min=1, max=10, step=1, default=6,
            weight_e=1.5, weight_g=0.7,
        ),
        SchemaField(
            id="shared_finances",
            label_zh="财务共享程度",
            label_en="Shared finances",
            kind="radio", default="separate",
            options=(
                ("separate", "完全分开", "separate"),
                ("mixed", "部分共享", "partially mixed"),
                ("joint", "完全共享", "fully joint"),
            ),
            weight_bv=1.0, weight_p=0.5,
        ),
        SchemaField(
            id="intimacy_quality",
            label_zh="亲密度 (1-10)",
            label_en="Intimacy quality",
            kind="slider", min=1, max=10, step=1, default=6,
            weight_e=1.8,
        ),
        SchemaField(
            id="growth_alignment",
            label_zh="成长方向一致 (1-10)",
            label_en="Growth alignment",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_g=1.5, weight_e=0.5,
            forward_eligible=True,
        ),
        SchemaField(
            id="external_validation",
            label_zh="外部认可 (家人朋友支持)",
            label_en="External validation",
            kind="slider", min=1, max=10, step=1, default=6,
            weight_bv=0.5,
        ),
        SchemaField(
            id="forward_step_taken",
            label_zh="已经迈过的关系节点(多选)",
            label_en="Forward steps taken",
            kind="multi", default=[],
            options=(
                ("met_family", "见家长", "met family"),
                ("cohabit", "同居", "cohabitation"),
                ("engagement", "订婚", "engagement"),
                ("co_pet", "共同养宠", "co-pet"),
                ("co_debt", "共同负债", "co-debt"),
                ("shared_dreams", "共同梦想", "shared dreams"),
            ),
            weight_bv=1.5,
        ),
        SchemaField(
            id="maintenance_cost",
            label_zh="维护成本 (1-10)",
            label_en="Maintenance cost",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_p=1.2,
        ),
        SchemaField(
            id="exit_cost",
            label_zh="退出成本 (1-10)",
            label_en="Exit cost",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_bv=0.5,  # exit cost ≈ accumulated 'capital'
        ),
    ),
)
