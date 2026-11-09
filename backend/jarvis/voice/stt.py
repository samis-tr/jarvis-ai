"""Speech-to-text: microphone capture (sounddevice) + faster-whisper (GPU if available).

The microphone is only opened while the user holds push-to-talk or explicitly starts a
single listening turn. There is no background recording.
"""
from __future__ import annotations

import functools

import asyncio
import logging
import os
import sys
import threading
import time
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)
SAMPLE_RATE = 16000
SUPPORTED_LANGS = ("ar", "de", "en")
MODEL_SIZES = {"tiny": 75, "base": 145, "small": 484, "medium": 1530, "large-v3-turbo": 1620}  # MB
_HF_REPOS = {"tiny": "Systran/faster-whisper-tiny", "base": "Systran/faster-whisper-base",
             "small": "Systran/faster-whisper-small", "medium": "Systran/faster-whisper-medium",
             "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo"}


def _add_cuda_dll_dirs() -> None:
    """Make pip-installed CUDA libraries (cuBLAS, cuDNN) discoverable on Windows."""
    if sys.platform != "win32":
        return
    import site
    for sp in site.getsitepackages():
        for sub in ("nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin"):
            d = Path(sp) / sub
            if d.is_dir():
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


def decode_file(path: str) -> np.ndarray:
    """Decode any audio file to 16 kHz mono float32 using ffmpeg (PyAV 19 broke faster-whisper's decoder)."""
    import shutil
    import subprocess
    exe = shutil.which("ffmpeg")
    if not exe:
        from faster_whisper.audio import decode_audio
        return decode_audio(path, sampling_rate=SAMPLE_RATE)
    out = subprocess.run([exe, "-nostdin", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"],
                         capture_output=True, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def model_downloaded(size: str) -> bool:
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(_HF_REPOS.get(size, size), local_files_only=True)
        return True
    except Exception:
        return False


class SpeechRecognizer:
    def __init__(self, bus, settings_getter):
        self.bus = bus
        self._settings = settings_getter
        self._model = None
        self._model_key = None
        self._device = None
        self._lock = threading.Lock()
        self._stream = None
        self._frames: list[np.ndarray] = []
        self._recording = False
        self._mode = "ptt"
        self._last_voice = 0.0
        self._started = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._done: asyncio.Future | None = None
        self.downloading = False
        self.last_error = ""

    # ------------------------------------------------------------------ model
    def status(self) -> dict:
        v = self._settings().voice
        return {"model": v.stt_model, "downloaded": model_downloaded(v.stt_model),
                "loaded": self._model is not None and self._model_key == v.stt_model, "device": self._device,
                "downloading": self.downloading, "size_mb": MODEL_SIZES.get(v.stt_model),
                "recording": self._recording, "mic_enabled": v.microphone_enabled, "error": self.last_error}

    def download(self) -> None:
        """Explicit, user-triggered model download."""
        from huggingface_hub import snapshot_download
        size = self._settings().voice.stt_model
        self.downloading = True
        try:
            snapshot_download(_HF_REPOS.get(size, size))
        finally:
            self.downloading = False

    def _load(self):
        v = self._settings().voice
        if self._model is not None and self._model_key == v.stt_model:
            return self._model
        if not model_downloaded(v.stt_model):
            raise RuntimeError(f"Speech model '{v.stt_model}' is not downloaded yet (Settings → Voice).")
        from faster_whisper import WhisperModel
        repo = _HF_REPOS.get(v.stt_model, v.stt_model)
        attempts = []
        if v.stt_device in ("auto", "cuda"):
            _add_cuda_dll_dirs()
            attempts.append(("cuda", "int8"))  # GTX 10xx (Pascal) has no fast FP16 -> int8
        if v.stt_device in ("auto", "cpu"):
            attempts.append(("cpu", "int8"))
        err = None
        for device, ctype in attempts:
            try:
                t0 = time.time()
                m = WhisperModel(repo, device=device, compute_type=ctype, local_files_only=True)
                # warm-up so the first real request is fast and CUDA errors surface now
                m.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language="en")
                self._model, self._model_key, self._device = m, v.stt_model, f"{device}/{ctype}"
                log.info("Whisper %s loaded on %s in %.1fs", v.stt_model, self._device, time.time() - t0)
                return m
            except Exception as e:
                err = e
                log.warning("Whisper on %s failed: %s", device, e)
        raise RuntimeError(f"Could not load speech model: {err}")

    def transcribe_array(self, audio: np.ndarray) -> dict:
        audio = normalize_gain(audio)
        with self._lock:
            model = self._load()
            lang = self._settings().voice.stt_language
            t0 = time.time()
            kw = dict(beam_size=5, vad_filter=True, vad_parameters={"min_silence_duration_ms": 500})
            segments, info = model.transcribe(audio, language=None if lang == "auto" else lang, **kw)
            if lang == "auto" and info.language not in SUPPORTED_LANGS:
                # Short dialect phrases are sometimes detected as e.g. French: retry with the best of ar/de/en.
                probs = dict(info.all_language_probs or [])
                best = max(SUPPORTED_LANGS, key=lambda code: probs.get(code, 0.0))
                segments, info = model.transcribe(audio, language=best, **kw)
            text = " ".join(s.text.strip() for s in segments).strip()
            return {"text": text, "language": info.language, "language_prob": round(info.language_probability, 2),
                    "duration_s": round(len(audio) / SAMPLE_RATE, 2), "elapsed_s": round(time.time() - t0, 2),
                    "device": self._device}

    def transcribe_file(self, path: str) -> dict:
        return self.transcribe_array(decode_file(path))

    # ------------------------------------------------------------------ microphone
    def start(self, loop: asyncio.AbstractEventLoop, mode: str = "ptt") -> asyncio.Future:
        v = self._settings().voice
        if not v.microphone_enabled:
            raise RuntimeError("Microphone is disabled in settings.")
        if self._recording:
            raise RuntimeError("Already listening.")
        import sounddevice as sd
        self._loop, self._mode = loop, mode
        self._frames = []
        self._done = loop.create_future()
        self._started = self._last_voice = time.time()
        self._recording = True

        def callback(indata, frames, t, status):
            try:
                _callback(indata)
            except Exception:  # an exception here would silently abort the audio stream
                log.exception("microphone callback failed")

        def _callback(indata):
            if not self._recording:
                return
            chunk = indata[:, 0].copy()
            self._frames.append(chunk)
            rms = float(np.sqrt(np.mean(chunk ** 2)) + 1e-9)
            level = min(1.0, rms * 12)
            now = time.time()
            if rms > 0.012:
                self._last_voice = now
            loop.call_soon_threadsafe(functools.partial(self.bus.emit, "audio_level", source="mic", level=round(level, 3)))
            silence = (now - self._last_voice) * 1000
            too_long = now - self._started > v.max_record_s
            heard = now - self._started > 1.0
            if too_long or (self._mode == "vad" and heard and silence > v.vad_silence_ms and self._has_speech()):
                loop.call_soon_threadsafe(self._auto_stop)

        self._stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=1600,
                                      device=v.input_device, callback=callback)
        self._stream.start()
        self.bus.set_phase("voice", "listening")
        self.bus.emit("voice", state="listening", mode=mode)
        return self._done

    def _has_speech(self) -> bool:
        return (self._last_voice - self._started) > 0.3

    def _auto_stop(self):
        if self._recording:
            self.stop()

    def stop(self) -> np.ndarray | None:
        if not self._recording:
            return None
        self._recording = False
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass
        self._stream = None
        audio = np.concatenate(self._frames) if self._frames else np.zeros(0, dtype=np.float32)
        self.bus.set_phase("voice", None)
        self.bus.emit("voice", state="stopped", seconds=round(len(audio) / SAMPLE_RATE, 2))
        if self._done and not self._done.done():
            self._done.set_result(audio)
        return audio

    def cancel(self):
        if self._recording:
            self._recording = False
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
            self._frames = []
            if self._done and not self._done.done():
                self._done.set_result(np.zeros(0, dtype=np.float32))
        self.bus.set_phase("voice", None)
        self.bus.emit("voice", state="cancelled")

    @property
    def recording(self) -> bool:
        return self._recording


def normalize_gain(audio: np.ndarray, target_peak: float = 0.5, max_gain: float = 20.0) -> np.ndarray:
    """Boost quiet microphones (low Windows input level) so Whisper and its VAD hear the speech."""
    if audio.size == 0:
        return audio
    peak = float(np.abs(audio).max())
    if peak < 1e-4 or peak >= target_peak:
        return audio
    return (audio * min(max_gain, target_peak / peak)).astype(np.float32)


def list_input_devices() -> list[dict]:
    try:
        import sounddevice as sd
        default_in = sd.default.device[0]
        return [{"index": i, "name": d["name"], "default": i == default_in}
                for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0 and d["hostapi"] == 0]
    except Exception as e:
        return [{"index": -1, "name": f"error: {e}", "default": False}]
