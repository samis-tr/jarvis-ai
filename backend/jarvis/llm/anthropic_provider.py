"""Anthropic Claude provider (PAID - billed per token to the user's Anthropic API account).

A Claude.ai / Claude Code subscription does NOT cover this; it needs an API key from
console.anthropic.com, stored in Windows Credential Manager.
"""
from __future__ import annotations

from jarvis.llm.base import ChatMessage, LLMError, LLMResponse, Provider, ToolCall

try:
    import anthropic
except Exception:  # pragma: no cover
    anthropic = None

# USD per million tokens (input, output) - shown in the UI so costs are never a surprise.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


class AnthropicProvider(Provider):
    name = "anthropic"
    paid = True

    def __init__(self, api_key: str, model: str = "claude-opus-5-5", effort: str = "medium", timeout: float = 120.0):
        if anthropic is None:
            raise LLMError("anthropic package not installed")
        self.client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=2)
        self.model = model
        self.effort = effort

    @staticmethod
    def _convert(messages: list[ChatMessage]) -> list[dict]:
        out: list[dict] = []
        pending_results: list[dict] = []
        for m in messages:
            if m.role == "tool":
                pending_results.append({"type": "tool_result", "tool_use_id": m.tool_call_id,
                                        "content": m.content, "is_error": m.is_error})
                continue
            if pending_results:  # all results of one turn go back in a single user message
                out.append({"role": "user", "content": pending_results})
                pending_results = []
            if m.role == "assistant":
                if m.raw is not None:
                    out.append({"role": "assistant", "content": m.raw})  # replay blocks unchanged (thinking etc.)
                else:
                    blocks: list[dict] = [{"type": "text", "text": m.content}] if m.content else []
                    blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.arguments} for c in m.tool_calls]
                    out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "…"}]})
            else:
                out.append({"role": "user", "content": m.content})
        if pending_results:
            out.append({"role": "user", "content": pending_results})
        return out

    async def chat(self, system, messages, tools):
        tool_defs = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
        try:
            resp = await self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=self._convert(messages),
                tools=tool_defs,
                output_config={"effort": self.effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise LLMError("Anthropic API key is invalid.") from e
        except anthropic.PermissionDeniedError as e:
            raise LLMError("Anthropic API key lacks permission for this model.") from e
        except anthropic.NotFoundError as e:
            raise LLMError(f"Unknown Claude model '{self.model}'.") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Anthropic rate limit reached - try again shortly.") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Anthropic API error {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Cannot reach the Anthropic API (network).") from e

        if resp.stop_reason == "refusal":
            return LLMResponse(text="I can't help with that request.", raw=resp.content, stop_reason="refusal")
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"]
        u = resp.usage
        usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens}
        price = PRICES.get(self.model)
        if price:
            usage["cost_usd"] = round(u.input_tokens / 1e6 * price[0] + u.output_tokens / 1e6 * price[1], 5)
        return LLMResponse(text=text.strip(), tool_calls=calls, raw=resp.content, usage=usage, stop_reason=resp.stop_reason)

    async def health(self):
        try:
            await self.client.models.retrieve(self.model)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}
