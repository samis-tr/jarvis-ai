# JARVIS AI — Architecture (Phase 1)

```
┌──────────────── Desktop window (pywebview → WebView2) ────────────────┐
│  React 19 + TypeScript + Vite + Tailwind 4  (frontend/)               │
│  Orb (canvas, real status + real audio levels) · Chat · Task/Approval │
│  History · Memory · Permissions · Settings · Emergency STOP           │
└───────────────▲ REST + WebSocket (127.0.0.1, per-launch token) ───────┘
                │
┌───────────────┴────────────── Python backend (backend/jarvis) ────────┐
│ server.py     FastAPI API, token + Host check, serves built UI        │
│ agent.py      Task engine: PLANNING → WAITING_FOR_APPROVAL →          │
│               EXECUTING → VERIFYING → COMPLETED/FAILED/CANCELLED      │
│               validation (Pydantic) · timeouts · retry limit · cancel │
│ security/     permissions.py (ALLOW/ASK/DENY in code), paths.py       │
│               (approved/protected dirs), redact.py, secrets.py        │
│               (Windows Credential Manager via keyring)                │
│ llm/          Provider interface: ollama · anthropic (SDK) ·          │
│               openai_compat · mock (offline, deterministic)           │
│ tools/        Typed tools (Pydantic args + risk + verify()):          │
│               apps · filesystem · system · browser · memory           │
│ memory.py     SQLite (WAL + FTS5): conversations, memories, tasks,    │
│               action log (all redacted)                               │
│ voice/        stt.py  faster-whisper (CUDA int8 on GTX 1060 → CPU)    │
│               tts.py  Edge neural voices (MP3 → played by the UI)     │
│ events.py     Event bus → WebSocket; global assistant phase           │
└────────────────────────────────────────────────────────────────────────┘
```

## Why these choices
* **pywebview instead of Tauri 2** – Tauri needs Rust + MSVC Build Tools (~6–8 GB);
  drive C: had 24 GB free. pywebview uses the already installed WebView2 runtime.
  The UI is plain Vite/React, so it can be wrapped by Tauri later without changes.
* **FastAPI on 127.0.0.1 + random token** instead of IPC – simple, testable; every
  request needs the token and a local Host header (blocks other websites/DNS rebinding).
* **Ollama `qwen3.5:4b`** (thinking off) – fits 6 GB VRAM with the speech model (~3.1 GB), supports tool
  calling and Arabic. (`qwen3:4b` is the *thinking* variant: ~30 s per reply → unusable.)
* **faster-whisper large-v3-turbo, int8 on CUDA** – Pascal GPUs have no fast FP16; int8
  works. Falls back to CPU automatically.
* **Edge TTS** – best free Arabic voices (incl. Syrian/Lebanese/Jordanian). Online.

## Security model
1. The LLM can only call registered tools; there is **no shell / install / payment /
   messaging tool**.
2. Every call: Pydantic validation → `assess()` (concrete risk + scope) → `decide()`.
   * LOW → run. MEDIUM → run only if pre-authorized *and* inside approved folders *and*
     the task has not read untrusted content; otherwise ask. HIGH → always ask.
   * Safe mode: every change asks; HIGH is blocked.
3. Untrusted content (web pages, files) is wrapped in `<untrusted_content>` and *taints*
   the task, so later changes require approval (prompt-injection defense).
4. Paths are resolved (no `..`/symlink tricks); Windows, Program Files, AppData, `.ssh`
   are never writable; `.env`, keys and password DBs are never readable.
5. Deletion goes to the Recycle Bin. Overwrite = HIGH risk.
6. Logs, action history, conversations and memories pass through secret redaction;
   memories that look like credentials are refused.
7. Paid providers require an explicit acknowledgement; there is no automatic fallback
   to a paid API.
8. Microphone is opened only during push-to-talk / an explicit "listen once" turn.

## Extension points (future phases)
* New tool = subclass `Tool` in `tools/`, add to the module's `TOOLS` list.
* New provider = implement `Provider.chat()` in `llm/`, register in `build_provider`.
* Event bus can be bridged to a phone companion / remote monitor.
* Task engine is ready for a background queue and scheduled workflows.
