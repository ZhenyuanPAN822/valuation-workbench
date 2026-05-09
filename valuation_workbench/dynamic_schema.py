"""LLM-schema → DynamicSchema validation. Permissive — fixes minor LLM drift."""
from __future__ import annotations

from typing import Any

from .models import DynamicField, DynamicSchema, DynamicStage, DynamicSubtheme
from .llm.schema_prompt import IB_PARAMS, FALLBACK_SCHEMA


_VALID_KINDS = {"likert5", "likert7", "number", "fillin", "select", "range"}


def _parse_field(raw: dict, idx: int, stage_id: str = "", sub_theme: str = "") -> DynamicField | None:
    if not isinstance(raw, dict):
        return None
    fid = str(raw.get("id") or raw.get("name") or "").strip()
    if not fid or fid.isdigit():
        fid = f"q_{stage_id or 'x'}_{idx+1}"
    kind = str(raw.get("kind") or raw.get("type") or "likert5").strip()
    if kind not in _VALID_KINDS:
        kind = "likert5"
    opts_in = raw.get("options") or []
    opts_out = []
    for o in opts_in:
        if isinstance(o, dict):
            opts_out.append((
                str(o.get("value", "")),
                str(o.get("label_zh", o.get("label", ""))),
                str(o.get("label_en", o.get("label", ""))),
            ))
        elif isinstance(o, (list, tuple)) and len(o) >= 1:
            opts_out.append((
                str(o[0]),
                str(o[1] if len(o) > 1 else o[0]),
                str(o[2] if len(o) > 2 else o[0]),
            ))
        elif isinstance(o, str):
            opts_out.append((o, o, o))
    mapping = raw.get("mapping") or {}
    scale = str(mapping.get("scale", "linear"))
    if scale not in ("linear", "inverse", "log"):
        scale = "linear"
    try:
        to_min = float(mapping.get("to_min", 0.0))
        to_max = float(mapping.get("to_max", 1.0))
    except (TypeError, ValueError):
        to_min, to_max = 0.0, 1.0
    ib_param = str(raw.get("ib_param") or "")
    if ib_param and ib_param not in IB_PARAMS:
        ib_param = ""

    if kind == "likert5":
        mn_default, mx_default = 1, 5
    elif kind == "likert7":
        mn_default, mx_default = 1, 7
    else:
        mn_default, mx_default = 0, 10

    try:
        mn = float(raw.get("min", mn_default))
    except (TypeError, ValueError):
        mn = float(mn_default)
    try:
        mx = float(raw.get("max", mx_default))
    except (TypeError, ValueError):
        mx = float(mx_default)
    try:
        step = float(raw.get("step", 1))
    except (TypeError, ValueError):
        step = 1.0
    default = raw.get("default", (mn + mx) / 2)

    label_zh = (raw.get("label_zh") or raw.get("question_zh") or raw.get("question")
                 or raw.get("label") or raw.get("text") or fid)
    label_en = raw.get("label_en") or label_zh

    return DynamicField(
        id=fid,
        label_zh=str(label_zh),
        label_en=str(label_en),
        kind=kind,
        hint_zh=str(raw.get("hint_zh") or raw.get("hint") or raw.get("help_zh") or ""),
        hint_en=str(raw.get("hint_en") or raw.get("hint") or ""),
        anchor_low_zh=str(raw.get("anchor_low_zh") or raw.get("anchor_low") or ""),
        anchor_high_zh=str(raw.get("anchor_high_zh") or raw.get("anchor_high") or ""),
        min=mn, max=mx, step=step, default=default,
        options=tuple(opts_out),
        ib_param=ib_param, scale=scale, to_min=to_min, to_max=to_max,
        stage_id=stage_id, sub_theme=sub_theme,
    )


def parse_dyn_schema(obj: dict) -> DynamicSchema:
    """Parse LLM JSON into DynamicSchema. Supports both flat (v0.2) and 6-stage (v0.3)."""
    if not isinstance(obj, dict):
        return get_fallback_schema()

    subject_kind = str(obj.get("subject_kind") or obj.get("kind") or "other")
    if subject_kind not in ("person", "crush", "relationship", "self", "other"):
        subject_kind = "other"

    stages_in = obj.get("stages") or []
    stages_out = []

    if stages_in and isinstance(stages_in, list):
        for st_idx, raw_st in enumerate(stages_in):
            if not isinstance(raw_st, dict):
                continue
            sid = str(raw_st.get("id") or f"B{st_idx+1}")
            sub_in = raw_st.get("sub_themes") or raw_st.get("subthemes") or []
            subs_out = []
            if sub_in and isinstance(sub_in, list):
                for sub_idx, raw_sub in enumerate(sub_in):
                    if not isinstance(raw_sub, dict):
                        continue
                    name = str(raw_sub.get("name_zh") or raw_sub.get("name") or f"子主题 {sub_idx+1}")
                    why = str(raw_sub.get("why_zh") or raw_sub.get("why") or "")
                    fs_in = raw_sub.get("fields") or raw_sub.get("questions") or []
                    fs_out = []
                    for fi, rf in enumerate(fs_in):
                        df = _parse_field(rf, fi, stage_id=sid, sub_theme=name)
                        if df:
                            fs_out.append(df)
                    if fs_out:
                        subs_out.append(DynamicSubtheme(name_zh=name, why_zh=why, fields=tuple(fs_out)))
            else:
                # No sub_themes — treat raw_st.fields as a single subtheme
                fs_in = raw_st.get("fields") or []
                fs_out = []
                for fi, rf in enumerate(fs_in):
                    df = _parse_field(rf, fi, stage_id=sid, sub_theme="主线")
                    if df:
                        fs_out.append(df)
                if fs_out:
                    subs_out.append(DynamicSubtheme(name_zh="主线", why_zh="", fields=tuple(fs_out)))
            if subs_out:
                stages_out.append(DynamicStage(
                    id=sid,
                    label_zh=str(raw_st.get("label_zh") or raw_st.get("label") or sid),
                    why_matters_zh=str(raw_st.get("why_matters_zh") or raw_st.get("why_matters") or ""),
                    sub_themes=tuple(subs_out),
                ))

    if stages_out:
        return DynamicSchema(
            title_zh=str(obj.get("title_zh") or obj.get("title") or "对象/暧昧估值问卷"),
            title_en="",
            subtitle_zh=str(obj.get("subtitle_zh") or obj.get("subtitle") or ""),
            subtitle_en="",
            subject_kind=subject_kind,
            stages=tuple(stages_out),
        )

    # Flat-schema fallback (v0.2 or LLM that ignored stages key)
    flat = obj.get("fields") or obj.get("questions") or obj.get("items") or []
    if flat:
        fields_out = []
        for fi, rf in enumerate(flat):
            df = _parse_field(rf, fi, stage_id="B0", sub_theme="通用")
            if df:
                fields_out.append(df)
        if fields_out:
            return DynamicSchema(
                title_zh=str(obj.get("title_zh") or obj.get("title") or "估值问卷"),
                title_en="",
                subtitle_zh=str(obj.get("subtitle_zh") or obj.get("subtitle") or ""),
                subtitle_en="",
                subject_kind=subject_kind,
                fields=tuple(fields_out),
            )

    return get_fallback_schema()


def get_fallback_schema() -> DynamicSchema:
    return parse_dyn_schema(FALLBACK_SCHEMA)
