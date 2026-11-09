"""Gemini / DeepSeek via their OpenAI-compatible APIs - offline (mocked HTTP), no cost."""
import json

import httpx
import pytest

from jarvis.llm import LLMError, build_provider
from jarvis.llm.base import ChatMessage
from jarvis.llm.openai_compat import OpenAICompatProvider


@pytest.mark.parametrize("name", ["gemini", "deepseek"])
def test_cloud_provider_never_silent(services, monkeypatch, name):
    monkeypatch.setattr("jarvis.llm.get_secret", lambda n: "k-test")
    services.store.update({"provider": {"active": name}})
    with pytest.raises(LLMError, match="cost"):
        build_provider(services.settings)                       # not acknowledged -> refused
    services.store.update({"provider": {"paid_acknowledged": {name: True}}})
    monkeypatch.setattr("jarvis.llm.get_secret", lambda n: None)
    with pytest.raises(LLMError, match="API key"):
        build_provider(services.settings)                       # acknowledged but no key -> refused
    monkeypatch.setattr("jarvis.llm.get_secret", lambda n: "k-test")
    p = build_provider(services.settings)
    assert p.name == name and p.paid


@pytest.mark.asyncio
async def test_tool_call_roundtrip_replays_native_message(monkeypatch):
    seen = []

    def handler(request: httpx.Request):
        seen.append(json.loads(request.content))
        if len(seen) == 1:
            msg = {"role": "assistant", "content": None, "reasoning_content": "think",
                   "tool_calls": [{"id": "", "type": "function",
                                   "function": {"name": "open_application", "arguments": '{"name": "notepad"}'},
                                   "extra_content": {"google": {"thought_signature": "sig"}}}]}
        else:
            msg = {"role": "assistant", "content": "تم."}
        return httpx.Response(200, json={"choices": [{"message": msg, "finish_reason": "stop"}], "usage": {}})

    transport = httpx.MockTransport(handler)
    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(transport=transport, **kw))
    p = OpenAICompatProvider("https://example.test/v1", "models/gemini-x", "k", name="gemini")
    tools = [{"name": "open_application", "description": "d",
              "parameters": {"type": "object", "properties": {"name": {"type": "string", "title": "Name"}}}}]
    r1 = await p.chat("sys", [ChatMessage("user", "افتح المفكرة")], tools)
    assert r1.tool_calls[0].name == "open_application" and r1.tool_calls[0].id
    assert seen[0]["model"] == "gemini-x"
    assert "title" not in json.dumps(seen[0]["tools"])
    msgs = [ChatMessage("user", "افتح المفكرة"), ChatMessage("assistant", r1.text, r1.tool_calls, raw=r1.raw),
            ChatMessage("tool", "ok", tool_call_id=r1.tool_calls[0].id)]
    r2 = await p.chat("sys", msgs, tools)
    replayed = seen[1]["messages"][2]
    assert replayed["reasoning_content"] == "think"
    assert replayed["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "sig"
    assert replayed["tool_calls"][0]["id"] == seen[1]["messages"][3]["tool_call_id"]
    assert r2.text == "تم."
