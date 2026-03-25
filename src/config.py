# config — tokens from .env everything else hardcoded in settings.py
# dont put ids in .env they live in settings like civilised people

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv
from src import settings


@dataclass
class Config:
    # only real secrets come from .env — the rest is in settings.py
    bot_token:    str
    tg_api_id:    int
    tg_api_hash:  str

    # ids and channels — pulled from settings.py not env
    owner_id:      int
    target_chat:   int
    learn_channel: int
    userbot_chats: List[int]

    # tuneable params — also from settings.py
    ollama_model:    str
    ollama_url:      str
    db_path:         str
    auto_post_hours: float

    @classmethod
    def from_env(cls) -> 'Config':
        # load .env — only tokens should be there nothing else
        load_dotenv()

        return cls(
            # tokens — if these are missing nothing works enjoy the crash
            bot_token   = os.getenv('BOT_TOKEN', ''),
            tg_api_id   = int(os.getenv('TG_API_ID') or 0),
            tg_api_hash = os.getenv('TG_API_HASH', ''),

            # ids — all hardcoded in settings.py where they belong
            owner_id      = settings.OWNER_ID,
            target_chat   = settings.TARGET_CHAT,
            learn_channel = settings.LEARN_CHANNEL,
            userbot_chats = settings.USERBOT_CHATS,

            # tuneable — settings.py is the source of truth here
            ollama_model    = settings.OLLAMA_MODEL,
            ollama_url      = settings.OLLAMA_URL,
            db_path         = settings.DB_PATH,
            auto_post_hours = settings.AUTO_POST_HOURS,
        )
