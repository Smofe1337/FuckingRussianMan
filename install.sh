#!/bin/bash
# works on macos and    /ubuntu
# detects os and does the right thing automatically

set -e
cd "$(dirname "$0")"

# detect os — only macos and ubuntu/debian are supported
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ -f /etc/debian_version ]] || grep -qi "ubuntu\|debian" /etc/os-release 2>/dev/null; then
    OS="ubuntu"
fi

if [[ "$OS" == "unknown" ]]; then
    echo "unsupported os — only macos and ubuntu/debian are supported"
    exit 1
fi

echo ""
echo "=================================="
echo "  telegram bot installer"
echo "  os detected: $OS"
echo "=================================="
echo ""

# ── 1. python ─────────────────────────────────────────────────────────────────
echo ">> checking python..."

if ! command -v python3 &>/dev/null; then
    echo "   python3 not found -- installing..."
    if [[ "$OS" == "macos" ]]; then
        if command -v brew &>/dev/null; then
            brew install python
        else
            echo "   homebrew not found"
            echo "   install python manually from https://python.org then rerun"
            exit 1
        fi
    elif [[ "$OS" == "ubuntu" ]]; then
        sudo apt-get update -qq
        sudo apt-get install -y python3 python3-pip python3-venv
    else
        echo "   install python3 from https://python.org then rerun"
        exit 1
    fi
fi

echo "   ok -- $(python3 --version)"

# ── 2. venv ───────────────────────────────────────────────────────────────────
echo ">> setting up venv..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   venv created"
else
    echo "   venv already exists"
fi

source venv/bin/activate

# ── 3. python deps ────────────────────────────────────────────────────────────
echo ">> installing python packages..."
pip install --quiet --upgrade pip
pip install --quiet aiogram ollama python-dotenv telethon chromadb
echo "   aiogram ollama python-dotenv telethon chromadb -- done"

# ── 4. ollama ─────────────────────────────────────────────────────────────────
echo ">> checking ollama..."

if ! command -v ollama &>/dev/null; then
    echo "   ollama not found -- installing..."

    if [[ "$OS" == "macos" ]]; then
        if command -v brew &>/dev/null; then
            brew install --quiet ollama
        else
            # direct download via official installer
            curl -fsSL https://ollama.com/install.sh | sh
        fi

    elif [[ "$OS" == "ubuntu" ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    fi

    echo "   ollama installed"
else
    echo "   ollama already installed -- $(ollama --version 2>/dev/null || echo ok)"
fi

# start ollama in background if its not running
if ! ollama list &>/dev/null 2>&1; then
    echo "   starting ollama in background..."
    if [[ "$OS" == "macos" ]]; then
        # on macos ollama runs as a menu bar app
        open -a Ollama 2>/dev/null || ollama serve &>/dev/null &
    else
        ollama serve &>/dev/null &
    fi
    sleep 4
fi

# ── 5. pull main model ────────────────────────────────────────────────────────
# read model from settings.py (default llama3)
MODEL=$(python3 -c "from src.settings import OLLAMA_MODEL; print(OLLAMA_MODEL)" 2>/dev/null || echo "llama3")

echo ">> checking model: $MODEL..."
if ollama list 2>/dev/null | grep -q "$MODEL"; then
    echo "   $MODEL already pulled"
else
    echo "   pulling $MODEL -- this takes a few minutes..."
    ollama pull "$MODEL"
    echo "   $MODEL ready"
fi

# ── 6. pull embed model for rag ───────────────────────────────────────────────
EMBED=$(python3 -c "from src.settings import EMBED_MODEL; print(EMBED_MODEL)" 2>/dev/null || echo "nomic-embed-text")

echo ">> checking embed model: $EMBED..."
if ollama list 2>/dev/null | grep -q "$EMBED"; then
    echo "   $EMBED already pulled"
else
    echo "   pulling $EMBED (~274 mb)..."
    ollama pull "$EMBED"
    echo "   $EMBED ready"
fi

# ── 7. check .env ─────────────────────────────────────────────────────────────
echo ">> checking .env..."

if [ ! -f ".env" ]; then
    echo "   .env not found -- create it with your tokens"
    exit 1
fi

BOT_TOKEN=$(grep "^BOT_TOKEN" .env | cut -d= -f2 | tr -d '[:space:]')
if [ -z "$BOT_TOKEN" ]; then
    echo "   BOT_TOKEN is empty in .env"
    exit 1
fi

echo "   .env looks good"

# ── 8. launch ─────────────────────────────────────────────────────────────────
echo ""
echo "=================================="
echo "  everything ready -- launching"
echo "  press ctrl+c to stop"
echo "=================================="
echo ""

python3 main.py
