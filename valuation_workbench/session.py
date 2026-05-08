"""Session save/load with version migration."""
from __future__ import annotations

import json
from datetime import datetime

from .models import Session


CURRENT_VERSION = "0.1.0"


def new_session(lang: str = "zh") -> Session:
    return Session(
        version=CURRENT_VERSION,
        saved_at=datetime.now().isoformat(timespec="seconds"),
        lang=lang,
    )


def save_session(session: Session) -> str:
    session.saved_at = datetime.now().isoformat(timespec="seconds")
    return json.dumps(session.to_dict(), indent=2, ensure_ascii=False)


def load_session(payload: str) -> Session:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("session must be an object")
    return Session(
        version=data.get("version", CURRENT_VERSION),
        saved_at=data.get("saved_at", ""),
        lang=data.get("lang", "zh"),
        stage=data.get("stage", "A"),
        target_type=data.get("target_type", ""),
        answers=dict(data.get("answers", {})),
        scenarios=dict(data.get("scenarios", {"bear": {}, "base": {}, "bull": {}})),
        forward_var=dict(data.get("forward_var", {})),
        notes=data.get("notes", ""),
    )
