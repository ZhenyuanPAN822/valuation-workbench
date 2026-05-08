"""Hard-exclusion + compatibility tests."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_no_chat_log_or_candlestick():
    """Hard-exclusion: no 聊天记录 / chat-log analysis or K线/candlestick in production code."""
    patterns = [r"chat[-_]log", r"聊天记录", r"OHLC", r"candlestick"]
    skip_dirs = {"__pycache__", ".git", "sample_outputs", "docs"}
    self_path = Path(__file__).resolve()
    for f in REPO.rglob("*.py"):
        if f.resolve() == self_path:
            continue
        if any(part in skip_dirs for part in f.parts):
            continue
        text = f.read_text(encoding="utf-8")
        for pat in patterns:
            assert not re.search(pat, text, re.IGNORECASE), f"violation in {f}: {pat}"


def test_pyproject_zero_runtime_deps():
    pp_path = REPO / "pyproject.toml"
    if not pp_path.exists():
        return
    pp = pp_path.read_text(encoding="utf-8")
    m = re.search(r"^dependencies\s*=\s*(\[[^\]]*\])", pp, re.MULTILINE)
    if m:
        assert m.group(1).strip() == "[]"
