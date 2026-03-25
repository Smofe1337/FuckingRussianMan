# botstate — one dataclass to rule all mutable runtime shit
# no module-level globals because globals are for cowards

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set

from src import settings


@dataclass
class BotState:
    # everything handlers need to read or mutate lives here
    # reply_mode: all | mention | off — controls when bot opens its mouth
    # pending_post: draft waiting to be published or cancelled
    # own_posts: texts we sent ourselves so we dont learn our own garbage
    # histories: per-chat conversation turns trimmed to MAX_HISTORY

    reply_mode:   str              = 'all'
    pending_post: str              = ''
    lang:         str              = 'en'
    own_posts:    Set[str]         = field(default_factory=set)
    histories:    Dict[int, List]  = field(default_factory=lambda: defaultdict(list))

    def add_history(self, chat_id: int, role: str, text: str) -> None:
        # appends turn then trims the tail so context doesnt eat all the ram
        self.histories[chat_id].append({'role': role, 'content': text})
        if len(self.histories[chat_id]) > settings.MAX_HISTORY:
            self.histories[chat_id] = self.histories[chat_id][-settings.MAX_HISTORY:]

    def get_history(self, chat_id: int) -> List[dict]:
        # returns a copy so callers cant accidentally mutate the real thing
        return list(self.histories[chat_id])
