"""Schema for 暧昧对象 (crush) valuation."""
from ..models import SchemaField, Schema


CRUSH_SCHEMA = Schema(
    target_type="crush",
    label_zh="给暧昧对象做估值",
    label_en="Crush Valuation",
    description_zh="把'TA 是不是值得继续'翻译成 IB 估值表。EPS / PE / DCF / sensitivity 全套。",
    description_en="Translate 'is TA worth pursuing' into an IB valuation table. EPS / PE / DCF / sensitivity tables.",
    fields=(
        SchemaField(
            id="relationship_age_months",
            label_zh="认识时长(月)",
            label_en="Known duration (months)",
            kind="slider", min=0, max=36, step=1, default=6,
            weight_bv=0.8, weight_p=0.3,
            forward_eligible=True,
        ),
        SchemaField(
            id="frequency_per_week",
            label_zh="每周联系次数",
            label_en="Contacts per week",
            kind="slider", min=0, max=14, step=1, default=4,
            weight_e=0.6, weight_p=0.5,
        ),
        SchemaField(
            id="response_quality",
            label_zh="TA 回应质量 (1-10)",
            label_en="Response quality (1-10)",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_e=1.5, weight_g=0.5,
        ),
        SchemaField(
            id="effort_balance",
            label_zh="付出平衡度 (1=全你, 10=全 TA)",
            label_en="Effort balance (1=all you, 10=all them)",
            kind="slider", min=1, max=10, step=1, default=4,
            weight_e=0.8, weight_p=-0.5,  # higher balance reduces your P
        ),
        SchemaField(
            id="exclusivity_signal",
            label_zh="排他性信号",
            label_en="Exclusivity signal",
            kind="radio", default="ambiguous",
            options=(
                ("clear", "明确独家", "clear"),
                ("ambiguous", "暧昧不清", "ambiguous"),
                ("explicitly_not", "明确非独家", "explicitly not"),
            ),
            weight_e=1.2, weight_vol=1.0,
        ),
        SchemaField(
            id="mutual_friends",
            label_zh="共同朋友数",
            label_en="Mutual friends",
            kind="slider", min=0, max=20, step=1, default=2,
            weight_bv=0.5,
        ),
        SchemaField(
            id="met_in_person",
            label_zh="是否线下见过",
            label_en="Met in person",
            kind="radio", default="yes",
            options=(("yes", "见过", "yes"), ("no", "未见", "no")),
            weight_bv=1.5, weight_e=0.5,
        ),
        SchemaField(
            id="commitment_signals",
            label_zh="承诺信号(多选)",
            label_en="Commitment signals (multi-select)",
            kind="multi", default=[],
            options=(
                ("liked_post", "朋友圈点赞", "liked posts"),
                ("intro_friends", "介绍朋友", "intro to friends"),
                ("mentioned_family", "提及家人", "mentioned family"),
                ("future_plans", "共同计划", "future plans"),
                ("proactive_care", "主动关心", "proactive care"),
                ("vulnerability", "主动倾诉", "vulnerability shared"),
            ),
            weight_e=0.6, weight_g=0.8,  # each signal counts
        ),
        SchemaField(
            id="your_weekly_hours",
            label_zh="你每周投入小时数",
            label_en="Your weekly hours",
            kind="slider", min=0, max=30, step=1, default=5,
            weight_p=1.5,
        ),
        SchemaField(
            id="alt_options_available",
            label_zh="你的备选质量 (1-10)",
            label_en="Your alt options quality",
            kind="slider", min=1, max=10, step=1, default=5,
            weight_vol=0.5,  # high alt options = lower opportunity cost = lower vol
        ),
    ),
)
