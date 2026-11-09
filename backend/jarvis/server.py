"""Local API (FastAPI) - bound to 127.0.0.1 and protected by a per-launch session token."""
from __future__ import annotations

import asyncio
import hmac
import logging
import secrets as pysecrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jarvis import __version__
from jarvis.config import PROJECT_ROOT
from jarvis.llm import LLMError, build_provider
from jarvis.memory import CATEGORIES, SensitiveContentError
from jarvis.security import secrets
from jarvis.services import Services
from jarvis.tools import system as system_tools
from jarvis.voice.stt import MODEL_SIZES, list_input_devices

log = logging.getLogger(__name__)
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
ALLOWED_SECRETS = {"anthropic_api_key", "openai_api_key", "gemini_api_key", "deepseek_api_key", "brave_api_key"}


class ChatIn(BaseModel):
    text: str
    conversation_id: str | None = None
    speak: bool = False


class ApprovalIn(BaseModel):
    step_id: str
    decision: Literal["approve", "deny", "approve_for_task"]


class MemoryIn(BaseModel):
    category: str = "fact"
    content: str


class SecretIn(BaseModel):
    name: str
    value: str


class TTSIn(BaseModel):
    text: str
    voice: str | None = None


class VoiceStartIn(BaseModel):
    mode: Literal["ptt", "vad"] = "ptt"
    conversation_id: str | None = None
    send: bool = True


def create_app(services: Services | None = None, token: str | None = None) -> FastAPI:
    token = token or pysecrets.token_urlsafe(24)
    holder: dict = {"s": services}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if holder["s"] is None:
            holder["s"] = Services()
        yield
        await holder["s"].shutdown()

    app = FastAPI(title="JARVIS AI", version=__version__, lifespan=lifespan)
    app.state.token = token

    def S() -> Services:
        return holder["s"]

    def auth(request: Request):
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "testserver"):
            raise HTTPException(403, "bad host")
        supplied = request.headers.get("x-jarvis-token") or request.query_params.get("token") or ""
        if not hmac.compare_digest(supplied, token):
            raise HTTPException(401, "invalid session token")

    api = Depends(auth)

    # ------------------------------------------------------------ status
    @app.get("/api/bootstrap", dependencies=[api])
    async def bootstrap():
        s = S()
        return {"version": __version__, "settings": s.settings.model_dump(), "status": s.bus.status,
                "tools": [{"name": t.name, "description": t.description, "risk": t.risk.value,
                           "enabled": t.name not in s.settings.security.disabled_tools} for t in s.tools.all()],
                "secrets": {n: secrets.has_secret(n) for n in ALLOWED_SECRETS},
                "voice": s.stt.status(), "stt_models": MODEL_SIZES, "memory_categories": CATEGORIES,
                "conversations": s.memory.conversations(30)}

    @app.get("/api/system", dependencies=[api])
    async def system():
        return await asyncio.to_thread(system_tools.snapshot)

    @app.get("/api/provider/health", dependencies=[api])
    async def provider_health():
        try:
            p = build_provider(S().settings)
        except LLMError as e:
            return {"ok": False, "error": str(e), "provider": S().settings.provider.active}
        h = await p.health()
        return {**h, "provider": p.name, "paid": p.paid}

    @app.get("/api/provider/models", dependencies=[api])
    async def provider_models(provider: str):
        """Live model list from a cloud provider (listing models is free). Requires a saved key."""
        from jarvis.llm.openai_compat import PRESETS, OpenAICompatProvider
        if provider not in PRESETS:
            raise HTTPException(400, "unknown provider")
        base_url, secret, _field, label = PRESETS[provider]
        key = secrets.get_secret(secret)
        if not key:
            return {"ok": False, "error": f"No {label} API key saved.", "models": []}
        try:
            models = await OpenAICompatProvider(base_url, "x", key, name=provider).list_models()
        except LLMError as e:
            return {"ok": False, "error": str(e), "models": []}
        return {"ok": True, "models": models}

    @app.get("/api/ollama/models", dependencies=[api])
    async def ollama_models():
        from jarvis.llm.ollama import OllamaProvider
        st = S().settings.provider
        return await OllamaProvider(st.ollama_url, st.ollama_model).health()

    # ------------------------------------------------------------ chat & tasks
    @app.post("/api/chat", dependencies=[api])
    async def chat(body: ChatIn):
        text = body.text.strip()
        if not text:
            raise HTTPException(400, "empty message")
        t = S().agent.submit(text[:8000], body.conversation_id, speak=body.speak)
        return {"task_id": t.id, "conversation_id": t.conversation_id}

    @app.post("/api/tasks/{task_id}/approval", dependencies=[api])
    async def approval(task_id: str, body: ApprovalIn):
        if not S().agent.resolve_approval(task_id, body.step_id, body.decision):
            raise HTTPException(404, "no pending approval")
        return {"ok": True}

    @app.post("/api/tasks/{task_id}/cancel", dependencies=[api])
    async def cancel(task_id: str):
        return {"ok": S().agent.cancel(task_id)}

    @app.get("/api/tasks", dependencies=[api])
    async def tasks(limit: int = 50):
        live = {t.id: t.public() for t in S().agent.tasks.values() if t.steps}
        stored = S().memory.tasks(limit)
        for r in stored:
            if r["id"] in live:
                r.update(state=live[r["id"]]["state"])
        return stored

    @app.get("/api/actions", dependencies=[api])
    async def actions(limit: int = 100):
        return S().memory.recent_actions(limit)

    @app.post("/api/open_url", dependencies=[api])
    async def open_url(body: dict):
        """User clicked a link in the chat: open it in the default browser (http/https only)."""
        from jarvis.tools.apps import OpenWebsite
        import webbrowser
        try:
            u = OpenWebsite.normalize(str(body.get("url", "")))
        except ValueError as e:
            raise HTTPException(400, str(e))
        webbrowser.open(u, new=2)
        return {"ok": True}

    @app.post("/api/stop", dependencies=[api])
    async def emergency_stop():
        return S().emergency_stop()

    # ------------------------------------------------------------ conversations
    @app.get("/api/conversations", dependencies=[api])
    async def conversations():
        return S().memory.conversations(50)

    @app.get("/api/conversations/{cid}", dependencies=[api])
    async def conversation(cid: str):
        return S().memory.messages(cid)

    @app.delete("/api/conversations/{cid}", dependencies=[api])
    async def delete_conversation(cid: str):
        S().memory.delete_conversation(cid)
        return {"ok": True}

    # ------------------------------------------------------------ memory
    @app.get("/api/memories", dependencies=[api])
    async def memories(q: str | None = None, category: str | None = None):
        m = S().memory
        return m.search_memories(q, 50) if q else m.list_memories(category)

    @app.post("/api/memories", dependencies=[api])
    async def add_memory(body: MemoryIn):
        try:
            return {"id": S().memory.add_memory(body.category, body.content, "user")}
        except (ValueError, SensitiveContentError) as e:
            raise HTTPException(400, str(e))

    @app.put("/api/memories/{mid}", dependencies=[api])
    async def edit_memory(mid: int, body: MemoryIn):
        try:
            S().memory.update_memory(mid, body.content, body.category)
        except KeyError:
            raise HTTPException(404, "not found")
        except (ValueError, SensitiveContentError) as e:
            raise HTTPException(400, str(e))
        return {"ok": True}

    @app.delete("/api/memories/{mid}", dependencies=[api])
    async def delete_memory(mid: int):
        S().memory.delete_memory(mid)
        return {"ok": True}

    @app.delete("/api/memories", dependencies=[api])
    async def clear_memories():
        S().memory.clear_memories()
        return {"ok": True}

    # ------------------------------------------------------------ settings & secrets
    @app.get("/api/settings", dependencies=[api])
    async def get_settings():
        return S().settings.model_dump()

    @app.patch("/api/settings", dependencies=[api])
    async def patch_settings(patch: dict):
        try:
            st = S().store.update(patch)
        except Exception as e:
            raise HTTPException(400, f"invalid settings: {e}")
        S().bus.emit("settings", settings=st.model_dump())
        return st.model_dump()

    @app.post("/api/secrets", dependencies=[api])
    async def set_secret(body: SecretIn):
        if body.name not in ALLOWED_SECRETS:
            raise HTTPException(400, "unknown secret")
        secrets.set_secret(body.name, body.value.strip())
        return {"ok": True}

    @app.delete("/api/secrets/{name}", dependencies=[api])
    async def delete_secret(name: str):
        if name not in ALLOWED_SECRETS:
            raise HTTPException(400, "unknown secret")
        secrets.delete_secret(name)
        return {"ok": True}

    # ------------------------------------------------------------ voice
    @app.get("/api/voice/status", dependencies=[api])
    async def voice_status():
        return {**S().stt.status(), "devices": list_input_devices()}

    @app.post("/api/voice/model/download", dependencies=[api])
    async def voice_download():
        s = S()
        if s.stt.downloading:
            return {"ok": True, "already": True}

        async def go():
            s.bus.emit("voice_model", state="downloading", model=s.settings.voice.stt_model)
            try:
                await asyncio.to_thread(s.stt.download)
                s.bus.emit("voice_model", state="ready", model=s.settings.voice.stt_model)
            except Exception as e:
                s.bus.emit("voice_model", state="error", error=str(e))
        asyncio.create_task(go())
        return {"ok": True}

    @app.post("/api/voice/start", dependencies=[api])
    async def voice_start(body: VoiceStartIn):
        s = S()
        try:
            fut = s.stt.start(asyncio.get_running_loop(), body.mode)
        except Exception as e:
            log.warning("voice start failed: %s", e)
            raise HTTPException(409, str(e))

        async def finish():
            audio = await fut
            if audio is None or len(audio) < 16000 * 0.4:
                log.info("voice: recording too short (%s samples)", 0 if audio is None else len(audio))
                s.bus.emit("transcript", text="", error="too_short")
                return
            s.bus.set_phase("voice", "transcribing")
            try:
                res = await asyncio.to_thread(s.stt.transcribe_array, audio)
            except Exception as e:
                log.exception("transcription failed")
                s.stt.last_error = str(e)
                s.bus.emit("transcript", text="", error=str(e))
                return
            finally:
                s.bus.set_phase("voice", None)
            s.bus.emit("transcript", **res)
            if body.send and res["text"]:
                t = s.agent.submit(res["text"], body.conversation_id, speak=True)
                s.bus.emit("voice_submitted", task_id=t.id, conversation_id=t.conversation_id)
        asyncio.create_task(finish())
        return {"ok": True, "mode": body.mode}

    @app.post("/api/voice/stop", dependencies=[api])
    async def voice_stop():
        S().stt.stop()
        return {"ok": True}

    @app.post("/api/voice/cancel", dependencies=[api])
    async def voice_cancel():
        S().stt.cancel()
        return {"ok": True}

    @app.post("/api/tts", dependencies=[api])
    async def tts(body: TTSIn):
        try:
            return await S().tts.synthesize(body.text, body.voice)
        except Exception as e:
            raise HTTPException(502, f"TTS failed: {e}")

    @app.get("/api/tts/{aid}", dependencies=[api])
    async def tts_audio(aid: str):
        data = S().tts.get(aid)
        if data is None:
            raise HTTPException(404, "expired")
        return Response(data, media_type="audio/mpeg")

    # ------------------------------------------------------------ websocket
    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        if not hmac.compare_digest(websocket.query_params.get("token", ""), token):
            await websocket.close(code=4401)
            return
        await websocket.accept()
        q = S().bus.subscribe()
        await websocket.send_json({"type": "status", **S().bus.status})
        try:
            while True:
                evt = await q.get()
                await websocket.send_json(evt)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            S().bus.unsubscribe(q)

    # ------------------------------------------------------------ frontend
    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}")
        async def spa(path: str):
            f = (FRONTEND_DIST / path).resolve()
            if path and f.is_file() and FRONTEND_DIST in f.parents:
                return FileResponse(f)
            return FileResponse(FRONTEND_DIST / "index.html", headers={"Cache-Control": "no-store"})
    else:
        @app.get("/")
        async def no_ui():
            return JSONResponse({"error": "frontend not built - run: cd frontend; npm install; npm run build"})

    return app
