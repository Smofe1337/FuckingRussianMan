# chat handler — listens in target_chat and replies as u
# keeps typing action alive while llm is cooking so it doesnt look sus

import asyncio
import logging
import random

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from src import settings
from src.ai.llm import LLMEngine
from src.bot.state import BotState
from src.config import Config

log = logging.getLogger(__name__)


def make_chat_router(
    bot: Bot,
    llm: LLMEngine,
    state: BotState,
    config: Config,
) -> Router:
    # returns a router that handles messages in target_chat only
    router = Router()

    async def _think_and_reply(message: Message, text: str) -> None:
        # runs llm in executor so the event loop doesnt choke
        # pings typing every 4s while model is thinking like a real human would
        state.add_history(message.chat.id, 'user', text)

        loop = asyncio.get_event_loop()
        # blocking call — must run in executor or everything freezes
        fut = loop.run_in_executor(
            None,
            llm.generate,
            text,
            list(state.get_history(message.chat.id)[:-1]),
        )

        # spam typing action while waiting for the model to stop being slow
        while not fut.done():
            await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            await asyncio.sleep(4)

        response = await fut
        if not response:
            return

        # delay based on response length — longer text = longer fake typing = more human
        words   = len(response.split())
        delay   = random.uniform(settings.MIN_TYPING_DELAY, settings.MAX_TYPING_DELAY) + words * settings.WORDS_PER_SECOND
        delay   = min(delay, settings.MAX_SEND_DELAY)

        elapsed = 0
        while elapsed < delay:
            await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            chunk    = min(4, delay - elapsed)
            await asyncio.sleep(chunk)
            elapsed += chunk

        state.add_history(message.chat.id, 'assistant', response)
        await message.reply(response)

    @router.message(F.chat.id == config.target_chat, ~F.text.startswith('/'))
    async def handle_chat(message: Message) -> None:
        # ignores bots and empty messages — checks reply mode then fires
        if not message.text or message.from_user.is_bot:
            return

        text     = message.text.strip()
        bot_info = await bot.get_me()
        # mentioned = tagged by username or replied to the bot directly
        mentioned = (
            f'@{bot_info.username}' in text
            or (
                message.reply_to_message
                and message.reply_to_message.from_user
                and message.reply_to_message.from_user.id == bot_info.id
            )
        )

        if state.reply_mode == 'off':
            return
        if state.reply_mode == 'mention' and not mentioned:
            return

        await _think_and_reply(message, text)

    return router
