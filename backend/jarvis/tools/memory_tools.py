"""Memory tools. Saving always requires the user's approval; credentials are refused."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from jarvis.memory import SensitiveContentError
from jarvis.tools.base import Assessment, Risk, Tool, ToolResult


class RememberArgs(BaseModel):
    category: Literal["preference", "project", "fact", "workflow"] = "fact"
    content: str = Field(..., description="Short self-contained fact to remember, e.g. 'User prefers answers in Arabic'")


class Remember(Tool):
    name = "remember"
    description = ("Save a useful long-term memory (user preference, project info, fact, reusable workflow). "
                   "Only when the user asks to remember something or clearly states a lasting preference. "
                   "Never store passwords or personal documents.")
    Args = RememberArgs
    risk = Risk.MEDIUM

    def assess(self, args, ctx):
        return Assessment(Risk.MEDIUM, False, f"Save memory [{args.category}]: {args.content}")

    async def run(self, args, ctx):
        if not ctx.settings.memory.enabled:
            return ToolResult(False, "Memory is disabled in settings.")
        try:
            mid = ctx.services.memory.add_memory(args.category, args.content, source="assistant")
        except SensitiveContentError as e:
            return ToolResult(False, str(e))
        return ToolResult(True, f"Saved memory #{mid}.", {"id": mid})


class RecallArgs(BaseModel):
    query: str


class Recall(Tool):
    name = "recall"
    description = "Search saved long-term memories."
    Args = RecallArgs
    risk = Risk.LOW

    async def run(self, args, ctx):
        if not ctx.settings.memory.enabled:
            return ToolResult(False, "Memory is disabled in settings.")
        rows = ctx.services.memory.search_memories(args.query)
        return ToolResult(True, "\n".join(f"#{r['id']} [{r['category']}] {r['content']}" for r in rows) or "Nothing found.",
                          {"count": len(rows)})


TOOLS = [Remember(), Recall()]
