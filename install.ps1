# windows installer -- run in powershell as administrator
# right click install.ps1 -> run with powershell
# or: powershell -ExecutionPolicy Bypass -File install.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "=================================="
Write-Host "  telegram bot installer (windows)"
Write-Host "=================================="
Write-Host ""

# ── 1. python ─────────────────────────────────────────────────────────────────
Write-Host ">> checking python..."

$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3") {
            $python = $cmd
            break
        }
    } catch {}
}

if (-not $python) {
    Write-Host "   python3 not found -- trying to install via winget..."
    try {
        winget install --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
        $python = "python"
        Write-Host "   python installed -- restart this script if it doesnt work"
    } catch {
        Write-Host "   winget failed -- install python manually from https://python.org"
        Write-Host "   make sure to check 'Add to PATH' during install"
        Read-Host "press enter to exit"
        exit 1
    }
}

$pyver = & $python --version 2>&1
Write-Host "   ok -- $pyver"

# ── 2. venv ───────────────────────────────────────────────────────────────────
Write-Host ">> setting up venv..."

if (-not (Test-Path "venv")) {
    & $python -m venv venv
    Write-Host "   venv created"
} else {
    Write-Host "   venv already exists"
}

# activate venv
$activateScript = ".\venv\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Host "   venv activation script not found -- something went wrong"
    exit 1
}
& $activateScript

# ── 3. python deps ────────────────────────────────────────────────────────────
Write-Host ">> installing python packages..."
& python -m pip install --quiet --upgrade pip
& python -m pip install --quiet aiogram ollama python-dotenv telethon chromadb
Write-Host "   aiogram ollama python-dotenv telethon chromadb -- done"

# ── 4. ollama ─────────────────────────────────────────────────────────────────
Write-Host ">> checking ollama..."

$ollamaInstalled = $null
try {
    $ollamaInstalled = & ollama --version 2>&1
} catch {}

if (-not $ollamaInstalled) {
    Write-Host "   ollama not found -- installing via winget..."
    try {
        winget install --id Ollama.Ollama --silent --accept-source-agreements --accept-package-agreements
        Write-Host "   ollama installed"
        # refresh path so ollama is found
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    } catch {
        Write-Host "   winget failed -- download ollama from https://ollama.com/download/windows"
        Write-Host "   install it then rerun this script"
        Read-Host "press enter to exit"
        exit 1
    }
} else {
    Write-Host "   ollama already installed"
}

# start ollama server if not running
try {
    & ollama list 2>&1 | Out-Null
} catch {
    Write-Host "   starting ollama server..."
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 4
}

# ── 5. pull main model ────────────────────────────────────────────────────────
# read model from settings.py
try {
    $MODEL = & python -c "from src.settings import OLLAMA_MODEL; print(OLLAMA_MODEL)" 2>&1
} catch {
    $MODEL = "llama3"
}
$MODEL = $MODEL.Trim()

Write-Host ">> checking model: $MODEL..."
$modelList = & ollama list 2>&1
if ($modelList -match $MODEL) {
    Write-Host "   $MODEL already pulled"
} else {
    Write-Host "   pulling $MODEL -- this takes a few minutes..."
    & ollama pull $MODEL
    Write-Host "   $MODEL ready"
}

# ── 6. pull embed model for rag ───────────────────────────────────────────────
try {
    $EMBED = & python -c "from src.settings import EMBED_MODEL; print(EMBED_MODEL)" 2>&1
} catch {
    $EMBED = "nomic-embed-text"
}
$EMBED = $EMBED.Trim()

Write-Host ">> checking embed model: $EMBED..."
$modelList = & ollama list 2>&1
if ($modelList -match [regex]::Escape($EMBED)) {
    Write-Host "   $EMBED already pulled"
} else {
    Write-Host "   pulling $EMBED (~274 mb)..."
    & ollama pull $EMBED
    Write-Host "   $EMBED ready"
}

# ── 7. check .env ─────────────────────────────────────────────────────────────
Write-Host ">> checking .env..."

if (-not (Test-Path ".env")) {
    Write-Host "   .env not found -- create it with your tokens"
    Read-Host "press enter to exit"
    exit 1
}

$envContent = Get-Content ".env" -Raw
if ($envContent -notmatch "BOT_TOKEN=\S+") {
    Write-Host "   BOT_TOKEN is empty in .env"
    Read-Host "press enter to exit"
    exit 1
}

Write-Host "   .env looks good"

# ── 8. launch ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=================================="
Write-Host "  everything ready -- launching"
Write-Host "  press ctrl+c to stop"
Write-Host "=================================="
Write-Host ""

& python main.py
