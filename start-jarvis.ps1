# Starts JARVIS AI.
#   .\start-jarvis.ps1            -> desktop window
#   .\start-jarvis.ps1 -Server    -> API + UI only (prints a URL for your browser)
param([switch]$Server, [int]$Port = 8765)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { Write-Host "Python venv missing. Run .\setup.ps1 first." -ForegroundColor Red; exit 1 }
if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
    Write-Host "Building UI..." -ForegroundColor Cyan
    Push-Location (Join-Path $root "frontend"); npm install --no-fund --no-audit; npm run build; Pop-Location
}

# Make sure the local Ollama server is running (free local AI)
$ollama = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"
try { Invoke-WebRequest "http://127.0.0.1:11434/api/version" -UseBasicParsing -TimeoutSec 2 | Out-Null }
catch { if (Test-Path $ollama) { Start-Process $ollama -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep 2 } }

$env:PYTHONIOENCODING = "utf-8"
Set-Location (Join-Path $root "backend")
$jarvisArgs = @("-m", "jarvis.main", "--port", $Port)
if ($Server) { $jarvisArgs += "--server" }
& $py @jarvisArgs
