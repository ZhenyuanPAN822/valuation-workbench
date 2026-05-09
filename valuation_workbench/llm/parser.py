"""Tolerant JSON extraction: direct parse → ```json``` fence → outer-brace slice."""
from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class ParseError(Exception):
    pass


def parse_llm_json(text: str) -> dict:
    """Extract a JSON object from possibly-noisy LLM output.

    Tries in order: direct parse, fenced block, outer-brace slice. Raises
    ParseError with the original snippet if all three fail.
    """
    if not isinstance(text, str) or not text.strip():
        raise ParseError("empty LLM response")

    s = text.strip()

    # Tier 1
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Tier 2: fenced
    m = _FENCE_RE.search(s)
    if m:
        candidate = m.group(1).strip()
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # Tier 3: outer-brace slice
    a = s.find("{")
    b = s.rfind("}")
    if a >= 0 and b > a:
        candidate = s[a : b + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    raise ParseError(f"could not extract JSON from: {s[:200]}")
