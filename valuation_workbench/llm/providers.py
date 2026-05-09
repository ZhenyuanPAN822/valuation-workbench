"""Multi-vendor LLM proxy using stdlib urllib only.

Browser-held keys: callers pass provider/api_key/model/messages. No env-var key
persistence. Patterned after AI-decision-engine-zh server.py.

Each provider exposes a model list + default + key placeholder for the UI.
Custom provider takes an OpenAI-compatible base_url and arbitrary model name.
Custom model name is also supported within any provider via the special
sentinel "__custom__" — the UI swaps to a textbox.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any


PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "o1", "o1-mini", "o3-mini"],
        "default_model": "gpt-4o-mini",
        "key_placeholder": "sk-...",
    },
    "deepseek": {
        "name": "DeepSeek",
        "endpoint": "https://api.deepseek.com/chat/completions",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
        "key_placeholder": "sk-...",
    },
    "anthropic": {
        "name": "Claude",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "models": ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
        "default_model": "claude-sonnet-4-6",
        "key_placeholder": "sk-ant-...",
    },
    "gemini": {
        "name": "Gemini",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        "default_model": "gemini-2.5-flash",
        "key_placeholder": "AIza...",
    },
    "custom": {
        "name": "自定义 (OpenAI 兼容)",
        "endpoint": "",
        "models": [],
        "default_model": "",
        "key_placeholder": "your-api-key",
    },
}


CUSTOM_MODEL_SENTINEL = "__custom__"


class ProviderError(Exception):
    pass


def _post(url: str, headers: dict, payload: dict, timeout: int = 180) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            err_body = str(e)
        raise ProviderError(f"HTTP {e.code}: {err_body}") from e
    except urllib.error.URLError as e:
        raise ProviderError(f"网络错误: {e.reason}") from e
    except Exception as e:
        raise ProviderError(f"未预期错误: {e}") from e


def _call_openai_compat(url: str, key: str, model: str, messages: list, max_tokens: int = 2400, temperature: float = 0.3) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    data = _post(url, headers, payload)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ProviderError(f"返回格式异常: {str(data)[:200]}") from e


def _call_anthropic(key: str, model: str, messages: list, max_tokens: int = 2400, temperature: float = 0.3) -> str:
    sys_text = ""
    chat = []
    for m in messages:
        if m.get("role") == "system":
            sys_text += (m.get("content") or "") + "\n"
        else:
            chat.append({"role": m["role"], "content": m["content"]})
    payload: dict[str, Any] = {"model": model, "messages": chat, "max_tokens": max_tokens, "temperature": temperature}
    if sys_text.strip():
        payload["system"] = sys_text.strip()
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    data = _post(PROVIDERS["anthropic"]["endpoint"], headers, payload)
    try:
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    except Exception as e:
        raise ProviderError(f"返回格式异常 (anthropic): {str(data)[:200]}") from e


def _call_gemini(key: str, model: str, messages: list, max_tokens: int = 2400, temperature: float = 0.3) -> str:
    contents = []
    sys_prefix = ""
    for m in messages:
        role = m.get("role")
        text = m.get("content") or ""
        if role == "system":
            sys_prefix += text + "\n"
            continue
        role_g = "model" if role == "assistant" else "user"
        if role == "user" and sys_prefix:
            text = sys_prefix + "\n" + text
            sys_prefix = ""
        contents.append({"role": role_g, "parts": [{"text": text}]})
    if sys_prefix and not contents:
        contents.append({"role": "user", "parts": [{"text": sys_prefix}]})
    url = f"{PROVIDERS['gemini']['endpoint']}/models/{model}:generateContent?key={key}"
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    headers = {"Content-Type": "application/json"}
    data = _post(url, headers, payload)
    try:
        cand = data["candidates"][0]
        return "".join(p.get("text", "") for p in cand["content"]["parts"])
    except Exception as e:
        raise ProviderError(f"返回格式异常 (gemini): {str(data)[:200]}") from e


def _resolve_model(provider: str, model: str) -> str:
    if not model or model == CUSTOM_MODEL_SENTINEL:
        return PROVIDERS.get(provider, {}).get("default_model", "")
    return model


def call_llm(
    provider: str,
    api_key: str,
    model: str,
    messages: list,
    *,
    endpoint: str = "",
    max_tokens: int = 2400,
    temperature: float = 0.3,
) -> str:
    """Dispatch to the correct provider and return raw assistant text."""
    if not provider:
        raise ProviderError("provider 不能为空")
    if not api_key:
        raise ProviderError("API key 不能为空")
    if not messages:
        raise ProviderError("messages 不能为空")

    model = _resolve_model(provider, model)

    if provider == "anthropic":
        m = model or PROVIDERS["anthropic"]["default_model"]
        return _call_anthropic(api_key, m, messages, max_tokens, temperature)
    if provider == "gemini":
        m = model or PROVIDERS["gemini"]["default_model"]
        return _call_gemini(api_key, m, messages, max_tokens, temperature)
    if provider == "custom":
        if not endpoint:
            raise ProviderError("自定义厂商需要提供 endpoint")
        return _call_openai_compat(endpoint, api_key, model or "default", messages, max_tokens, temperature)
    if provider in ("openai", "deepseek"):
        url = PROVIDERS[provider]["endpoint"]
        m = model or PROVIDERS[provider]["default_model"]
        return _call_openai_compat(url, api_key, m, messages, max_tokens, temperature)
    raise ProviderError(f"未知 provider: {provider}")


def probe_connection(provider: str, api_key: str, model: str = "", endpoint: str = "") -> dict:
    """Send a tiny probe and return {ok: bool, content?: str, error?: str}."""
    probe = [{"role": "user", "content": "请用'连接成功'四个字回复，不要其他文字。"}]
    try:
        text = call_llm(provider, api_key, model, probe, endpoint=endpoint, max_tokens=50, temperature=0.0)
        return {"ok": True, "content": (text or "").strip()[:100]}
    except ProviderError as e:
        return {"ok": False, "error": str(e)[:300]}
    except Exception as e:
        return {"ok": False, "error": f"未预期: {e}"[:300]}
