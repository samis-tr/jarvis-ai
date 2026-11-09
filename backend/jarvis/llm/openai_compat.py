"""Any OpenAI-compatible /chat/completions endpoint (OpenAI, OpenRouter, Groq, LM Studio, vLLM ...)."""
from __future__ import annotations

import json
import uuid

import httpx

from jarvis.llm.base import ChatMessage, LLMError, LLMResponse, Provider, ToolCall


# Hosted services that speak the OpenAI chat-completions protocol: id -> (base URL, secret name, settings field, label)
PRESETS: dict[str, tuple[str, str, str, str]] = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini_api_key", "gemini_model", "Google Gemini"),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek_api_key", "deepseek_model", "DeepSeek"),
}

_NOT_CHAT = ("embedding", "imagen", "veo", "tts", "image", "aqa", "audio", "live", "learnlm", "robotics")


def _strip_titles(schema):
    """Gemini's OpenAI layer accepts a subset of JSON Schema; 'title' keys are noise there."""
    if isinstance(schema, dict):
        return {k: _strip_titles(v) for k, v in schema.items() if k != "title" or not isinstance(v, str)}
    if isinstance(schema, list):
        return [_strip_titles(x) for x in schema]
    return schema


class OpenAICompatProvider(Provider):
    name = "openai_compat"

    def __init__(self, base_url: str, model: str, api_key: str | None, timeout: float = 120.0, name: str = "openai_compat"):
        if not model:
            raise LLMError("No model configured for the OpenAI-compatible provider.")
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model.removeprefix("models/")
        self.api_key = api_key
        self.timeout = timeout
        host = httpx.URL(self.base_url).host
        self.paid = host not in ("localhost", "127.0.0.1")

    @staticmethod
    def _convert(system: str, messages: list[ChatMessage]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m.role == "assistant" and isinstance(m.raw, dict):
                out.append(m.raw)  # provider-native message, replayed unchanged
            elif m.role == "assistant":
                d: dict = {"role": "assistant", "content": m.content or None}
                if m.tool_calls:
                    d["tool_calls"] = [{"id": c.id, "type": "function",
                                        "function": {"name": c.name, "arguments": json.dumps(c.arguments, ensure_ascii=False)}}
                                       for c in m.tool_calls]
                out.append(d)
            elif m.role == "tool":
                out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
            else:
                out.append({"role": "user", "content": m.content})
        return out

    async def chat(self, system, messages, tools):
        body: dict = {"model": self.model, "messages": self._convert(system, messages)}
        if tools:
            if self.name == "gemini":
                tools = [_strip_titles(t) for t in tools]
            body["tools"] = [{"type": "function", "function": t} for t in tools]
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
        except httpx.HTTPError as e:
            raise LLMError(f"Cannot reach {self.base_url}: {e}") from e
        if r.status_code >= 400:
            raise LLMError(f"Provider error {r.status_code}: {r.text[:300]}")
        data = r.json()
        msg = data["choices"][0]["message"]
        calls = []
        for tc in msg.get("tool_calls") or []:
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            tc["id"] = tc.get("id") or uuid.uuid4().hex[:10]  # keep the replayed message consistent
            calls.append(ToolCall(tc["id"], tc["function"]["name"], args))
        raw = {k: v for k, v in msg.items() if v is not None and k not in ("refusal", "annotations", "audio")}
        raw["role"] = "assistant"
        return LLMResponse(text=(msg.get("content") or "").strip(), tool_calls=calls, raw=raw, usage=data.get("usage", {}),
                           stop_reason=data["choices"][0].get("finish_reason"))

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self.base_url}/models",
                                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})
        except httpx.HTTPError as e:
            raise LLMError(f"Cannot reach {self.base_url}: {e}") from e
        if r.status_code >= 400:
            raise LLMError(f"Provider error {r.status_code}: {r.text[:300]}")
        ids = [str(m.get("id", "")).removeprefix("models/") for m in r.json().get("data", [])]
        return sorted(i for i in ids if i and not any(x in i.lower() for x in _NOT_CHAT))

    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=6) as c:
                r = await c.get(f"{self.base_url}/models",
                                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})
            return {"ok": r.status_code < 400, "error": None if r.status_code < 400 else r.text[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}
