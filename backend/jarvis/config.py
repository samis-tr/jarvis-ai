"""Application settings, persisted as JSON in the data directory.

Secrets (API keys) are NEVER stored here - they live in Windows Credential
Manager via `jarvis.security.secrets`.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("JARVIS_DATA_DIR", PROJECT_ROOT / "data"))
DEFAULT_WORKSPACE = Path.home() / "Documents" / "JARVIS"

ProviderName = Literal["mock", "ollama", "anthropic", "openai_compat", "gemini", "deepseek"]


class ProviderSettings(BaseModel):
    active: ProviderName = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3.5:4b"
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: Literal["low", "medium", "high"] = "medium"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    gemini_model: str = "gemini-2.5-flash"
    deepseek_model: str = "deepseek-chat"
    # Paid providers must be explicitly acknowledged by the user before use.
    paid_acknowledged: dict[str, bool] = Field(default_factory=dict)
    request_timeout_s: float = 120.0


class VoiceSettings(BaseModel):
    microphone_enabled: bool = True
    stt_model: str = "large-v3-turbo"  # faster-whisper model (see voice.stt.MODEL_SIZES)
    stt_device: Literal["auto", "cuda", "cpu"] = "auto"
    stt_language: Literal["auto", "ar", "de", "en"] = "auto"
    tts_enabled: bool = True
    tts_voice_ar: str = "ar-LB-RamiNeural"  # Levantine; clearer than the SY voices in tests
    tts_voice_de: str = "de-DE-ConradNeural"
    tts_voice_en: str = "en-GB-RyanNeural"
    vad_silence_ms: int = 900
    max_record_s: int = 30
    input_device: int | None = None


class SecuritySettings(BaseModel):
    safe_mode: bool = False
    approved_dirs: list[str] = Field(default_factory=lambda: [str(DEFAULT_WORKSPACE)])
    # Medium-risk tools that may run without asking when the target is inside approved_dirs.
    auto_approve_medium: list[str] = Field(default_factory=lambda: ["create_folder", "create_file"])
    disabled_tools: list[str] = Field(default_factory=list)
    approval_timeout_s: int = 300
    tool_timeout_s: int = 90


class WebSettings(BaseModel):
    browser_visible: bool = False  # visible window needs `playwright install chromium` (~170 MB)
    # Wikimedia's API policy requires contact info (e-mail or URL) in the User-Agent. Optional.
    wikipedia_contact: str = ""


class MemorySettings(BaseModel):
    enabled: bool = True
    save_conversations: bool = True


class Settings(BaseModel):
    ui_language: Literal["ar", "de", "en"] = "ar"
    assistant_name: str = "JARVIS"
    user_name: str = ""
    provider: ProviderSettings = Field(default_factory=ProviderSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    web: WebSettings = Field(default_factory=WebSettings)


class SettingsStore:
    """Thread-safe JSON settings persistence."""

    def __init__(self, path: Path | None = None):
        self.path = path or (DATA_DIR / "settings.json")
        self._lock = threading.Lock()
        self._settings = self._load()

    def _load(self) -> Settings:
        if self.path.exists():
            try:
                return Settings.model_validate_json(self.path.read_text(encoding="utf-8"))
            except Exception:  # corrupt file -> keep a backup, start fresh
                self.path.rename(self.path.with_suffix(".corrupt.json"))
        return Settings()

    @property
    def settings(self) -> Settings:
        return self._settings

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(self._settings.model_dump_json(indent=2), encoding="utf-8")
            os.replace(tmp, self.path)

    def update(self, patch: dict) -> Settings:
        """Deep-merge a partial dict into the settings and validate."""
        with self._lock:
            merged = _deep_merge(self._settings.model_dump(), patch)
            self._settings = Settings.model_validate(merged)
        self.save()
        return self._settings


def _deep_merge(base: dict, patch: dict) -> dict:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
