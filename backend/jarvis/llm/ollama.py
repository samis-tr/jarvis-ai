"""Local Ollama provider (free, runs on this PC)."""
from __future__ import annotations

import json
import uuid

import httpx

from jarvis.llm.base import ChatMessage, LLMError, LLMResponse, Provider, ToolCall


class OllamaProvider(Provider):
    name = "ollama"
    paid = False

    def __init__(self, url: str, model: str, timeout: float = 120.0):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @staticmethod
    def _convert(system: str, messages: list[ChatMessage]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            if m.role == "assistant":
                d: dict = {"role": "assistant", "content": m.content}
                if m.tool_calls:
                    d["tool_calls"] = [{"function": {"name": c.name, "arguments": c.arguments}} for c in m.tool_calls]
                out.append(d)
            elif m.role == "tool":
                out.append({"role": "tool", "content": m.content, "tool_name": m.tool_name or ""})
            else:
                out.append({"role": "user", "content": m.content})
        return out

    async def chat(self, system, messages, tools):
        body = {
            "model": self.model,
            "messages": self._convert(system, messages),
            "stream": False,
            "think": False,  # qwen3: skip slow hidden reasoning for snappy replies
            "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": 1536},  # cap runaway generations
        }
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in tools]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.post(f"{self.url}/api/chat", json=body)
                if r.status_code == 400 and "think" in r.text:
                    body.pop("think")
                    r = await c.post(f"{self.url}/api/chat", json=body)
        except httpx.ConnectError as e:
            raise LLMError("Ollama is not running. Start the Ollama app (or run 'ollama serve').") from e
        except httpx.TimeoutException as e:
            raise LLMError("Ollama timed out.") from e
        if r.status_code == 404:
            raise LLMError(f"Ollama model '{self.model}' not found. Run: ollama pull {self.model}")
        if r.status_code >= 400:
            raise LLMError(f"Ollama error {r.status_code}: {r.text[:300]}")
        data = r.json()
        msg = data.get("message", {})
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            calls.append(ToolCall(id=uuid.uuid4().hex[:10], name=fn.get("name", ""), arguments=args))
        text = msg.get("content", "") or ""
        if "<think>" in text:  # strip any leaked reasoning
            text = text.split("</think>")[-1].strip()
        return LLMResponse(text=text.strip(), tool_calls=calls, usage={
            "input_tokens": data.get("prompt_eval_count"), "output_tokens": data.get("eval_count")},
            stop_reason=data.get("done_reason"))

    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=4) as c:
                v = (await c.get(f"{self.url}/api/version")).json()
                tags = (await c.get(f"{self.url}/api/tags")).json()
        except Exception as e:
            return {"ok": False, "error": f"Ollama not reachable: {e}"}
        models = [m["name"] for m in tags.get("models", [])]
        return {"ok": self.model in models or f"{self.model}:latest" in models, "version": v.get("version"),
                "models": models, "error": None if self.model in models else f"model {self.model} not installed"}
