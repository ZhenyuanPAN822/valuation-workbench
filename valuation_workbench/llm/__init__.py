"""LLM layer: multi-vendor proxy + schema generation prompt + tolerant JSON parser.

Architecture mirrors AI-decision-engine-zh: browser holds API keys, server is a thin
proxy with no key persistence. Vendors share the OpenAI chat-completions shape;
Anthropic/Gemini use vendor-specific bodies.
"""
from .providers import call_llm, PROVIDERS, ProviderError, probe_connection, CUSTOM_MODEL_SENTINEL
from .parser import parse_llm_json, ParseError
from .schema_prompt import build_schema_prompt, FALLBACK_SCHEMA, IB_PARAMS, SIX_STAGES
from .forward_prompt import (
    build_forward_prompt, FALLBACK_FORWARD,
    schema_to_summary, answers_to_summary, ib_to_summary,
)
from .narrative_prompt import (
    build_narrative_prompt, fallback_narrative,
    valuation_to_summary, archetype_to_summary, forward_to_summary,
)

__all__ = [
    "call_llm", "PROVIDERS", "ProviderError", "probe_connection", "CUSTOM_MODEL_SENTINEL",
    "parse_llm_json", "ParseError",
    "build_schema_prompt", "FALLBACK_SCHEMA", "IB_PARAMS", "SIX_STAGES",
    "build_forward_prompt", "FALLBACK_FORWARD",
    "schema_to_summary", "answers_to_summary", "ib_to_summary",
    "build_narrative_prompt", "fallback_narrative",
    "valuation_to_summary", "archetype_to_summary", "forward_to_summary",
]
