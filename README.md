# FuckingRussianMan

A Telegram AI bot that learns from your messages and writes exactly like you
Runs on a local LLM via Ollama — no cloud, no data leaks, no bullshit

---

## What it does

- Replies in your chat as you (via Telethon userbot)
- Learns from your channel posts
- RAG — picks the most relevant examples from the database for each prompt
- Auto-posts to your channel on a schedule
- RU/EN localization
- Simulates typing delay so it doesn't look like a bot

---

## Quick start

### 1. Clone the repo

```bash
git clone https://github.com/Smofe1337/FuckingRussianMan.git
cd FuckingRussianMan
```

### 2. Create `.env` with your tokens

```env
BOT_TOKEN   = 1234567890:ABCdefGhIjKlMnOpQrStUvWxYz  # replace
TG_API_ID   = 12345678                                # replace
TG_API_HASH = a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4       # replace
```

- `BOT_TOKEN` — get it from [@BotFather](https://t.me/BotFather)
- `TG_API_ID` and `TG_API_HASH` — get them at [my.telegram.org](https://my.telegram.org)

### 3. Set your chat IDs in `src/settings.py`

```python
OWNER_ID      = 123456789        # your user id — get it from t.me/userinfobot
TARGET_CHAT   = -1001234567890   # chat where the bot replies
LEARN_CHANNEL = -1001234567890   # channel to learn from and post to
USERBOT_CHATS = [-1001234567890] # chats where the userbot replies as you
```

### 4. Run the installer

**macOS / Ubuntu / Debian:**
```bash
chmod +x install.sh && ./install.sh
```

**Windows:**
```powershell
.\install.ps1
```

The installer handles Python dependencies, Ollama, and model downloads automatically

---

## Manual setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py
```

---

## Settings

Everything lives in `src/settings.py`

| Setting | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3` | Model used for text generation |
| `EMBED_MODEL` | `nomic-embed-text` | Model used for RAG embeddings |
| `AUTO_POST_HOURS` | `0.1` | Auto-post interval in hours |
| `CHAT_NUM_PREDICT` | `50` | Max tokens per chat reply |
| `POST_NUM_PREDICT` | `180` | Max tokens per generated post |
| `DEBUG` | `True` | Verbose logging |

---

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) with `llama3` and `nomic-embed-text` pulled
- Telegram Bot Token + API credentials
