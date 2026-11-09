"""Integration tests against real local services. Run with:  $env:JARVIS_INTEGRATION=1; pytest -m integration -s"""
import asyncio
from pathlib import Path

import pytest

from jarvis.agent import State

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
def real(services):
    services.store.update({"provider": {"active": "ollama"}})
    return services


async def test_ollama_text_answer_arabic(real):
    t = await real.agent.wait(real.agent.submit("شو هي عاصمة ألمانيا؟ جاوب بجملة وحدة.").id, timeout=180)
    print("\nOLLAMA:", t.result, t.usage)
    assert t.state is State.COMPLETED and any("؀" <= c <= "ۿ" for c in t.result)  # answered in Arabic (4B model may be factually wrong)


async def test_ollama_creates_document(real):
    ws = Path(real.settings.security.approved_dirs[0])
    t = await real.agent.wait(real.agent.submit(
        "Create a test document called acceptance-test.md in my workspace containing a short shopping list.").id, 240)
    print("\nRESULT:", t.result, [(s.tool, s.status) for s in t.steps])
    assert t.state is State.COMPLETED
    files = list(ws.rglob("*.md"))
    assert files and any(s.tool == "create_file" and s.verified for s in t.steps)


async def test_tts_edge_arabic(real):
    info = await real.tts.synthesize("أهلاً، أنا جارفيس. كيف فيني ساعدك اليوم؟")
    print("\nTTS:", info)
    assert info["bytes"] > 5000 and info["voice"].startswith("ar-")


async def test_voice_pipeline_roundtrip(real, tmp_path):
    """Spoken Arabic (synthesized) -> Whisper on GPU -> agent -> spoken reply. Mic hardware is not involved."""
    from jarvis.voice.stt import model_downloaded
    if not model_downloaded(real.settings.voice.stt_model):
        pytest.skip("speech model not downloaded")
    spoken = "افتح المفكرة لو سمحت"
    info = await real.tts.synthesize(spoken, "ar-LB-RamiNeural")
    mp3 = tmp_path / "q.mp3"
    mp3.write_bytes(real.tts.get(info["id"]))
    res = await asyncio.to_thread(real.stt.transcribe_file, str(mp3))
    print("\nSTT:", res)
    assert res["language"] == "ar" and "المفكرة" in res["text"]
    answer = await real.agent.wait(real.agent.submit("ما هي عاصمة سوريا؟ جملة وحدة").id, 180)
    reply = await real.tts.synthesize(answer.result)
    print("REPLY:", answer.result, reply)
    assert reply["bytes"] > 3000


async def test_browser_research(real):
    from jarvis.security.secrets import has_secret
    if not (has_secret("brave_api_key") or real.settings.web.wikipedia_contact):
        pytest.skip("no legitimate search source configured (Brave key or Wikipedia contact)")
    from jarvis.tools.base import ToolContext
    from jarvis.tools.browser import ResearchTopic
    tool = ResearchTopic()
    args = tool.parse({"topic": "faster-whisper speech recognition", "pages": 2})
    res = await tool.run(args, ToolContext(real.settings, real))
    print("\nSOURCES:", res.data.get("sources"))
    await real.browser.shutdown()
    assert res.ok and res.untrusted and len(res.data["sources"]) >= 1
