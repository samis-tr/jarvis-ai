"""Text-to-speech with Microsoft Edge neural voices (edge-tts).

Free, but it uses Microsoft's online speech service (the text is sent to Microsoft).
Audio is returned as MP3 and played by the UI, which also drives the visualizer from it.
"""
from __future__ import annotations

import re
import time
import uuid
from collections import OrderedDict

MAX_CHARS = 1800


def detect_language(text: str) -> str:
    if re.search(r"[؀-ۿ]", text):
        return "ar"
    if re.search(r"[äöüß]|\b(und|der|die|das|ist|nicht|ich|Sie|habe|wird|mit)\b", text, re.I):
        return "de"
    return "en"


def clean_for_speech(text: str) -> str:
    t = re.sub(r"```.*?```", " ", text, flags=re.S)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"[*_#`>|\[\]]", "", t)
    t = re.sub(r"\(\s*\)", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > MAX_CHARS:
        cut = t[:MAX_CHARS]
        t = cut[: max(cut.rfind("."), cut.rfind("。"), cut.rfind("؟"), 200)] + "."
    return t


class Speaker:
    def __init__(self, settings_getter):
        self._settings = settings_getter
        self._cache: OrderedDict[str, tuple[bytes, float]] = OrderedDict()

    def voice_for(self, lang: str) -> str:
        v = self._settings().voice
        return {"ar": v.tts_voice_ar, "de": v.tts_voice_de}.get(lang, v.tts_voice_en)

    async def synthesize(self, text: str, voice: str | None = None) -> dict:
        import edge_tts
        clean = clean_for_speech(text)
        if not clean:
            raise ValueError("nothing to speak")
        lang = detect_language(clean)
        voice = voice or self.voice_for(lang)
        t0 = time.time()
        audio = bytearray()
        com = edge_tts.Communicate(clean, voice)
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
        if not audio:
            raise RuntimeError("TTS returned no audio")
        aid = uuid.uuid4().hex[:12]
        self._cache[aid] = (bytes(audio), time.time())
        while len(self._cache) > 20:
            self._cache.popitem(last=False)
        return {"id": aid, "voice": voice, "language": lang, "bytes": len(audio), "elapsed_s": round(time.time() - t0, 2)}

    def get(self, aid: str) -> bytes | None:
        item = self._cache.get(aid)
        return item[0] if item else None
