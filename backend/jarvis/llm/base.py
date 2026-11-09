"""Provider-independent chat types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatMessage:
    role: Literal["user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    tool_name: str | None = None
    is_error: bool = False
    raw: Any = None  # provider-native content (e.g. Claude content blocks incl. thinking) for faithful replay


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None
    usage: dict[str, Any] = field(default_factory=dict)
    stop_reason: str | None = None


class LLMError(RuntimeError):
    pass


class Provider:
    name: str = "base"
    paid: bool = False

    async def chat(self, system: str, messages: list[ChatMessage], tools: list[dict]) -> LLMResponse:  # pragma: no cover
        raise NotImplementedError

    async def health(self) -> dict:
        return {"ok": True}
