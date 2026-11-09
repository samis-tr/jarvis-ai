"""Service container wiring all subsystems together."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from jarvis.config import DATA_DIR, SettingsStore
from jarvis.events import EventBus
from jarvis.memory import MemoryStore
from jarvis.security.paths import resolve
from jarvis.tools import build_registry
from jarvis.tools.browser import BrowserService
from jarvis.voice.stt import SpeechRecognizer
from jarvis.voice.tts import Speaker

log = logging.getLogger(__name__)


class Services:
    def __init__(self, data_dir: Path | None = None, *, headless_browser: bool = True):
        self.data_dir = data_dir or DATA_DIR
        self.store = SettingsStore(self.data_dir / "settings.json")
        self.bus = EventBus()
        self.memory = MemoryStore(self.data_dir / "jarvis.db")
        self.tools = build_registry()
        self.browser = BrowserService(headless=headless_browser, settings_getter=lambda: self.settings)
        self.stt = SpeechRecognizer(self.bus, lambda: self.settings)
        self.tts = Speaker(lambda: self.settings)
        for d in self.settings.security.approved_dirs[:1]:
            resolve(d).mkdir(parents=True, exist_ok=True)
        from jarvis.agent import AgentEngine
        self.agent = AgentEngine(self)

    @property
    def settings(self):
        return self.store.settings

    def speak_later(self, text: str) -> None:
        async def _go():
            try:
                info = await self.tts.synthesize(text)
                self.bus.emit("speak", **info)
            except Exception as e:
                log.warning("TTS failed: %s", e)
                self.bus.emit("speak_error", error=str(e))
        asyncio.get_running_loop().create_task(_go())

    def emergency_stop(self) -> dict:
        n = self.agent.cancel_all("EMERGENCY STOP")
        self.stt.cancel()
        self.bus.emit("stop_audio")
        self.bus.emit("emergency_stop", cancelled=n)
        return {"cancelled_tasks": n}

    async def shutdown(self):
        self.agent.cancel_all("shutdown")
        self.stt.cancel()
        await self.browser.shutdown()
        self.memory.close()
