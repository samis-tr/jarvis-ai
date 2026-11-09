# JARVIS AI

A local-first, voice-enabled desktop assistant for Windows 10/11 (Arabic · Deutsch · English).
Phase 1 (functional MVP). See [PROGRESS.md](PROGRESS.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Start

```powershell
cd D:\jarvis-ai
.\start-jarvis.ps1            # desktop window
.\start-jarvis.ps1 -Server    # browser mode: open the printed http://127.0.0.1:8765/?token=... URL
```

If PowerShell blocks scripts: `powershell -ExecutionPolicy Bypass -File .\start-jarvis.ps1`

## First-time setup (already done on this PC)

```powershell
winget install Ollama.Ollama
.\setup.ps1
```

## Using it
* **Type** in the message box, or **hold PTT** (or `Ctrl+Space`) and speak; release to send.
  "Listen once" records until you stop talking. The mic button disables the microphone completely.
* `Esc` stops speech. **Emergency stop** (top bar) cancels all tasks, recording and speech.
* Actions needing permission appear as amber cards in *Current task* → Approve / Deny.
* Files are created in `Documents\JARVIS` by default (Permissions → approved folders).

## AI providers & costs
| Provider | Cost | Notes |
|---|---|---|
| Ollama `qwen3.5:4b` (default) | free, local | GTX 1060, ~3 GB VRAM. Fine for chat, Arabic, single tool calls. `qwen3:4b-instruct` = faster, weaker alternative. |
| Anthropic Claude API | **paid per token** (Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50 per 1M) | Needs an API key from console.anthropic.com — a Claude.ai / Claude Code subscription does **not** include API usage. Must be acknowledged in Settings. |
| OpenAI-compatible | depends on endpoint | LM Studio / vLLM (local, free) or hosted APIs. |
| Mock | free | Offline test mode, no AI. |

Free online services used: Microsoft Edge TTS (spoken text goes to Microsoft), web pages you research.
Optional: Brave Search API key (free tier) or a Wikipedia contact for research.

## Tests
```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest                         # unit + workflow tests (mock AI)
$env:JARVIS_INTEGRATION=1; ..\.venv\Scripts\python.exe -m pytest -m integration -s   # real Ollama / TTS / web
```
