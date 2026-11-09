# One-time setup for JARVIS AI (Windows 10/11). Installs everything inside this folder,
# except Ollama (system app) and model downloads, which are explicit steps below.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "1/4 Python virtual environment" -ForegroundColor Cyan
if (-not (Test-Path ".venv\Scripts\python.exe")) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip -q
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

Write-Host "2/4 User interface" -ForegroundColor Cyan
Push-Location frontend; npm install --no-fund --no-audit; npm run build; Pop-Location

Write-Host "3/4 Local AI model (Ollama)" -ForegroundColor Cyan
$ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollama)) { Write-Host "Ollama not installed. Install with:  winget install Ollama.Ollama" -ForegroundColor Yellow }
else { & $ollama pull qwen3.5:4b }

Write-Host "4/4 Browser for web research (Playwright Chromium, ~170 MB)" -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m playwright install chromium-headless-shell

Write-Host "`nDone. The speech model is downloaded from Settings -> Voice (or on first use)." -ForegroundColor Green
Write-Host "Start JARVIS with:  .\start-jarvis.ps1" -ForegroundColor Green
