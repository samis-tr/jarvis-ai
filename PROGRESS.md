# PROGRESS — JARVIS AI

_Last update: 2026-11-08_

## Environment (detected)
Windows 11 Home · i7-8750H (6C/12T) · 15.8 GB RAM · NVIDIA GTX 1060 6 GB (CC 6.1, driver 580.88) ·
Python 3.12.10 · Node 24.20 · Git · ffmpeg · WebView2 157 · no Rust → **pywebview instead of Tauri**.
Project lives on `D:\jarvis-ai` (the first location had a path > 260 chars, which broke Playwright's DLLs).

## Milestone 1 — Backend core ✅
- [x] Settings (JSON), secrets in Windows Credential Manager, redacted rotating logs
- [x] Permission manager (LOW/MEDIUM/HIGH, safe mode, allowlist, approved/protected folders, per-task grants, taint after untrusted content)
- [x] Task engine with states PLANNING → WAITING_FOR_APPROVAL → EXECUTING → VERIFYING → COMPLETED/FAILED/CANCELLED, timeouts, retry limit, cancel, emergency stop, action log
- [x] SQLite memory (FTS5 incl. Arabic), conversations, tasks, actions; sensitive-content refusal
- [x] Providers: Ollama, Anthropic (official SDK), OpenAI-compatible, Mock
- [x] Tools: open/close app, open website, list/find/read/create/append/move files, delete → Recycle Bin, system info, top processes, screenshot, web search, browse page, research topic, browser tabs, remember/recall

## Milestone 2 — Voice ✅ (see verification below)
- [x] Push-to-talk + "listen once" with energy VAD, mic master switch, live levels to the orb
- [x] faster-whisper (CUDA int8 → CPU fallback), explicit model download from Settings
- [x] Edge TTS (Arabic Syrian/Lebanese/Jordanian, German, English voices), interruptible playback

## Milestone 3 — Desktop UI ✅
- [x] React/TS/Vite/Tailwind, RTL Arabic + German + English
- [x] Orb driven by real status + real audio levels, chat, task progress & approval cards, live CPU/RAM/GPU gauges
- [x] Task history, memory manager, permissions, settings (provider, keys, voice, web), emergency STOP

## Not done yet (Phase 2/3 — not claimed)
- Explicit up-front multi-step planner (today the model plans step by step; each batch of calls is shown before execution)
- Screen reading/OCR, keyboard/mouse automation, UI Automation, form filling, script runner
- Background task queue, wake word "Hey Jarvis", reusable workflows, plugins, installer, Tauri packaging

## Verification (2026-11-08, real UI at http://127.0.0.1:8765, Ollama qwen3:4b-instruct on GTX 1060)
| # | Scenario | Result |
|---|---|---|
| 1 | Text question "شو هي عاصمة فرنسا؟" | ✅ "عاصمة فرنسا هي باريس." (~8–12 s) |
| 2 | Spoken question → spoken answer | ✅ pipeline verified with synthesized Arabic speech: Whisper large-v3-turbo (CUDA int8) transcribed "افتح المفكرة لو سمحت" exactly; answer spoken with Edge TTS. ⚠️ Live microphone not yet tested (needs you to talk). |
| 3 | "افتح المفكرة" / "سكّر المفكرة" | ✅ opened + verified (LOW, no prompt). Close = MEDIUM → approval card → closed gracefully (WM_CLOSE, never force-kill) + verified. Denying a wrong tool call was respected. |
| 4 | "أنشئ ملف اسمه ui-test.md فيه قائمة مشتريات" | ✅ `Documents\JARVIS\ui-test.md` created, verified on disk |
| 5 | "ابحث عن faster-whisper ولخّصلي مع المصادر" | ✅ real results (GitHub, PyPI, Hugging Face) + correct Arabic summary with sources. Without a Brave key, search uses Bing pages in the automation browser, which can be blocked or noisy at times → set a Brave key or Wikipedia contact in Settings for reliability. |

Tests: `pytest` 16 passed; integration (`JARVIS_INTEGRATION=1`) 4 passed, 1 skipped (research test needs Brave key / Wikipedia contact).

### Known limitations (honest)
- The 4B local model sometimes picks the wrong tool on Levantine wording (once tried a screenshot / Sticky Notes for "سكّر"). Mitigated by verb hints in tool descriptions; MEDIUM/HIGH actions still always need approval, so a wrong choice cannot do harm silently. Its general knowledge in Arabic is limited — use Claude (paid) for higher quality.
- Visible automation browser needs `.venv\Scripts\python -m playwright install chromium` (headless works now).
- Edge TTS is an online Microsoft service (free); STT and the LLM run fully local.

## Model comparison (2026-11-08) → default switched to `qwen3.5:4b`
Same 11 prompts (Arabic facts, German, Levantine commands, tool choice), thinking off:

| | qwen3:4b-instruct | qwen3.5:4b |
|---|---|---|
| Score | 8/11 | 9/11 (one "miss" = looked up Syria's population on the web instead of guessing — arguably better) |
| "أكبر كوكب" | wrong ("الكواكب") | ✅ المشتري |
| "سكّر المفكرة" | close_application('notebook') (now handled by alias) | ✅ close_application('notepad') |
| create_file | asked to overwrite (HIGH risk) | ✅ no overwrite |
| Runaway answer | once 52 s | none |
| Speed | ~1–1.5 s short reply, 37 tok/s | ~3–5 s short reply (longer answers), 28 tok/s |
| VRAM | ~3.9 GB @8k ctx | ~3.1 GB |

Both still wrong on some world knowledge (e.g. author of "One Hundred Years of Solitude") — use Gemini/Claude for knowledge-heavy questions.
Also added: Ollama `num_predict` cap (1536) so a runaway generation can no longer block JARVIS for minutes.
Integration tests with qwen3.5:4b: 4 passed, 1 skipped.
