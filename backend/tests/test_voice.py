"""Microphone recording path with a fake sound device (no hardware needed)."""
import asyncio
import threading

import numpy as np
import pytest

from jarvis.voice.stt import SAMPLE_RATE, SpeechRecognizer, normalize_gain


class FakeStream:
    """Feeds 100 ms blocks of a 440 Hz tone to the callback from a background thread, like PortAudio does."""

    def __init__(self, samplerate, channels, dtype, blocksize, device, callback):
        self.cb, self.block, self._stop = callback, blocksize, threading.Event()

    def start(self):
        def run():
            t = 0
            while not self._stop.is_set():
                x = 0.2 * np.sin(2 * np.pi * 440 * (np.arange(self.block) + t) / SAMPLE_RATE)
                self.cb(x.astype(np.float32).reshape(-1, 1), self.block, None, None)
                t += self.block
                self._stop.wait(0.1)
        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._stop.set()

    def close(self):
        pass


@pytest.mark.asyncio
async def test_recording_collects_audio_and_levels(services, monkeypatch):
    import sounddevice
    monkeypatch.setattr(sounddevice, "InputStream", FakeStream)
    levels = []
    services.bus.subscribe(lambda ev: levels.append(ev) if ev.get("type") == "audio_level" else None) \
        if hasattr(services.bus, "subscribe") and False else None
    orig = services.bus.emit

    def spy(event, **kw):
        if event == "audio_level":
            levels.append(kw["level"])
        return orig(event, **kw)
    monkeypatch.setattr(services.bus, "emit", spy)

    rec = SpeechRecognizer(services.bus, lambda: services.settings)
    fut = rec.start(asyncio.get_running_loop(), "ptt")
    await asyncio.sleep(0.8)
    rec.stop()
    audio = await fut
    await asyncio.sleep(0.05)
    assert len(audio) >= SAMPLE_RATE * 0.5          # recording kept running (regression: callback crashed after 1 block)
    assert levels and max(levels) > 0.5              # live levels reached the UI/orb


def test_normalize_gain_boosts_quiet_audio():
    quiet = (0.01 * np.ones(1000)).astype(np.float32)
    assert abs(float(np.abs(normalize_gain(quiet)).max()) - 0.2) < 1e-6   # capped at 20x
    loud = (0.8 * np.ones(10)).astype(np.float32)
    assert normalize_gain(loud) is loud
    silent = np.zeros(10, dtype=np.float32)
    assert float(np.abs(normalize_gain(silent)).max()) == 0.0
