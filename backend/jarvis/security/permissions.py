"""Permission manager: decides ALLOW / ASK / DENY for every tool call.

The decision is made in code, independent of the LLM. Nothing the model says
(or any web page / document it read) can grant a permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from jarvis.config import Settings
from jarvis.tools.base import Assessment, Risk, Tool


class Decision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class Verdict:
    decision: Decision
    reason: str


@dataclass
class TaskGrants:
    """Per-task approvals given by the user ('allow this tool for the rest of this task')."""
    tools: set[str]
    tainted: bool = False  # task has ingested untrusted web/document content


def decide(tool: Tool, assessment: Assessment, settings: Settings, grants: TaskGrants) -> Verdict:
    sec = settings.security
    if tool.name in sec.disabled_tools:
        return Verdict(Decision.DENY, "tool is disabled in permission settings")

    risk = assessment.risk
    if risk is Risk.HIGH:
        if sec.safe_mode:
            return Verdict(Decision.DENY, "high-risk actions are blocked in safe mode")
        return Verdict(Decision.ASK, "high-risk action always requires explicit approval")

    if risk is Risk.LOW:
        if sec.safe_mode and tool.name in {"take_screenshot"}:
            return Verdict(Decision.ASK, "safe mode")
        return Verdict(Decision.ALLOW, "low risk")

    # MEDIUM
    if sec.safe_mode:
        return Verdict(Decision.ASK, "safe mode: every change needs approval")
    if grants.tainted:
        return Verdict(Decision.ASK, "task has read untrusted web/document content")
    if not assessment.in_scope:
        return Verdict(Decision.ASK, "target is outside the authorized scope")
    if tool.name in grants.tools:
        return Verdict(Decision.ALLOW, "approved earlier in this task")
    if tool.name in sec.auto_approve_medium:
        return Verdict(Decision.ALLOW, "pre-authorized for approved directories")
    return Verdict(Decision.ASK, "medium-risk action")
