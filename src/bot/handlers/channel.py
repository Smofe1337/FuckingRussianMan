# channel handler — watches learn_channel and eats every post it sees
# skips anything we sent ourselves so the bot doesnt learn its own garbage

import logging

from aiogram import F, Router
from aiogram.types import Message

from src.ai.rag import RAGIndex
from src.bot.state import BotState
from src.config import Config
from src.storage.database import Database

log = logging.getLogger(__name__)


def make_channel_router(
    db: Database,
    rag: RAGIndex,
    state: BotState,
    config: Config,
) -> Router:
    # returns a router that lurks in learn_channel and saves what it finds
    router = Router()

    @router.channel_post(F.chat.id == config.learn_channel)
    async def handle_channel_post(message: Message) -> None:
        # skip short garbage — anything under 15 chars isnt worth learning
        text = (message.text or message.caption or '').strip()
        if len(text) <= 15:
            return

        # skip our own posts — learning them would be a snake eating its tail
        if text in state.own_posts:
            state.own_posts.discard(text)
            log.info('skipping own post -> %s…', text[:60])
            return

        db.save_learned(text, source='channel')
        rag.add_text(text)
        log.info('learned from channel -> %s…', text[:60])

    return router
