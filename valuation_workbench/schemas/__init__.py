"""Per-target dynamic schemas.

Stages are fixed (A/B/C/D); fields per stage are dynamic per target type.
"""
from .person import PERSON_SCHEMA
from .crush import CRUSH_SCHEMA
from .relationship import RELATIONSHIP_SCHEMA
from .self_eval import SELF_SCHEMA


_SCHEMAS = {
    "person": PERSON_SCHEMA,
    "crush": CRUSH_SCHEMA,
    "relationship": RELATIONSHIP_SCHEMA,
    "self": SELF_SCHEMA,
}

TARGET_LABELS = {
    "person": ("人 / Person",),
    "crush": ("暧昧对象 / Crush",),
    "relationship": ("一段感情 / Relationship",),
    "self": ("自己 / Self",),
}


def list_targets() -> tuple:
    return tuple(_SCHEMAS.keys())


def get_schema(target_type: str):
    return _SCHEMAS.get(target_type)
