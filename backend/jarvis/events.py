"""In-process event bus feeding the UI over WebSocket, plus the live assistant status."""
from __future__ import annotations

import asyncio
import time
from typing import Any


class EventBus:
    def __init__(self):
        self._subs: set[asyncio.Queue] = set()
        self.status: dict[str, Any] = {"phase": "idle", "detail": "", "since": time.time()}
        self._busy: dict[str, str] = {}  # source -> phase, e.g. {"task:ab12": "thinking", "voice": "listening"}

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def emit(self, type_: str, **payload) -> None:
        evt = {"type": type_, "ts": time.time(), **payload}
        for q in list(self._subs):
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                pass  # slow consumer; drop rather than block the assistant

    # Status priority: the orb shows the most "active" phase across sources.
    _PRIORITY = ["waiting_approval", "listening", "transcribing", "executing", "thinking", "speaking", "idle"]

    def set_phase(self, source: str, phase: str | None, detail: str = "") -> None:
        if phase is None or phase == "idle":
            self._busy.pop(source, None)
        else:
            self._busy[source] = phase
        phases = list(self._busy.values()) or ["idle"]
        top = min(phases, key=lambda p: self._PRIORITY.index(p) if p in self._PRIORITY else 99)
        if top != self.status["phase"] or detail:
            self.status = {"phase": top, "detail": detail, "since": time.time()}
            self.emit("status", **self.status)
