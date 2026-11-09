"""Provider factory. Paid providers are never activated silently."""
from __future__ import annotations

from jarvis.config import Settings
from jarvis.llm.base import LLMError, Provider
from jarvis.security.secrets import get_secret

PAID_PROVIDERS = {"anthropic", "openai_compat", "gemini", "deepseek"}


def build_provider(settings: Settings) -> Provider:
    p = settings.provider
    if p.active == "mock":
        from jarvis.llm.mock import MockProvider
        return MockProvider()
    if p.active == "ollama":
        from jarvis.llm.ollama import OllamaProvider
        return OllamaProvider(p.ollama_url, p.ollama_model, p.request_timeout_s)
    if p.active == "anthropic":
        if not p.paid_acknowledged.get("anthropic"):
            raise LLMError("Claude API is a paid service. Confirm the cost notice in Settings before using it.")
        key = get_secret("anthropic_api_key")
        if not key:
            raise LLMError("No Anthropic API key saved. Add it in Settings (stored in Windows Credential Manager).")
        from jarvis.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(key, p.anthropic_model, p.anthropic_effort, p.request_timeout_s)
    if p.active == "openai_compat":
        from jarvis.llm.openai_compat import OpenAICompatProvider
        prov = OpenAICompatProvider(p.openai_base_url, p.openai_model, get_secret("openai_api_key"), p.request_timeout_s)
        if prov.paid and not p.paid_acknowledged.get("openai_compat"):
            raise LLMError("This endpoint may be a paid service. Confirm the cost notice in Settings before using it.")
        return prov
    if p.active in ("gemini", "deepseek"):
        from jarvis.llm.openai_compat import PRESETS, OpenAICompatProvider
        base_url, secret, field, label = PRESETS[p.active]
        if not p.paid_acknowledged.get(p.active):
            raise LLMError(f"{label} is a cloud service that can cost money. Confirm the cost notice in Settings before using it.")
        key = get_secret(secret)
        if not key:
            raise LLMError(f"No {label} API key saved. Add it in Settings (stored in Windows Credential Manager).")
        return OpenAICompatProvider(base_url, getattr(p, field), key, p.request_timeout_s, name=p.active)
    raise LLMError(f"Unknown provider {p.active}")
