# Development: backend in server mode with a fixed local token (for the browser preview / `npm run dev`).
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:JARVIS_DEV_TOKEN = "devtoken-local-preview"
$env:PYTHONIOENCODING = "utf-8"
Set-Location (Join-Path $root "backend")
& (Join-Path $root ".venv\Scripts\python.exe") -m jarvis.main --server --port 8765
