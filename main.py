# entry point — wires everything together and yeets bot + userbot at the same time
# if something breaks here you fucked up the config not the code

import asyncio
import logging

from src import settings

# logging setup — debug=true means u get spammed debug=false means only the important shit
_FMT = '%(asctime)s [%(levelname)s] %(name)s  %(message)s'

if settings.DEBUG:
    logging.basicConfig(level=logging.DEBUG, format=_FMT)
else:
    logging.basicConfig(level=logging.WARNING, format=_FMT)
    # keep startup loggers visible even in prod so u know its alive
    for _name in (
        '__main__',
        'src.bot.bot',
        'src.userbot.client',
        'src.scheduler.autopost',
    ):
        logging.getLogger(_name).setLevel(logging.INFO)

from src.ai.llm import LLMEngine
from src.ai.rag import RAGIndex
from src.bot.bot import TelegramBot
from src.bot.state import BotState
from src.config import Config
from src.scheduler.autopost import AutoPoster
from src.storage.database import Database
from src.userbot.client import Userbot

log = logging.getLogger(__name__)


async def main() -> None:
    # step 1 — grab config before anything else blows up
    config = Config.from_env()

    # step 2 — sqlite up first because everything else needs it
    db = Database(db_path=config.db_path)

    # step 3 — ai stack — rag needs db llm needs both
    rag = RAGIndex(db=db, ollama_url=config.ollama_url)
    llm = LLMEngine(db=db, rag=rag, model=config.ollama_model, ollama_url=config.ollama_url)

    # step 4 — shared state bag passed around everywhere
    state = BotState()

    # step 5 — userbot stays quiet if no api creds — not our problem
    userbot = Userbot(db=db, llm=llm, config=config)

    # step 6 — autoposter needs its own aiogram bot instance for dms
    # cant reuse the one inside TelegramBot because its not created yet here
    from aiogram import Bot as AiogramBot
    _aiogram_bot = AiogramBot(token=config.bot_token)

    async def _publish_fn(text: str) -> None:
        # prefer userbot so it looks like u wrote it — fall back to bot api if disconnected
        state.own_posts.add(text)
        if userbot.is_connected:
            await userbot.post(text)
            log.info('auto-post via userbot: %s…', text[:60])
        else:
            await _aiogram_bot.send_message(config.learn_channel, text)
            log.info('auto-post via bot api: %s…', text[:60])

    async def _notify_fn(text: str) -> None:
        # dm the owner so they know the post went through
        await _aiogram_bot.send_message(
            config.owner_id,
            f'Auto-post published:\n\n{text}',
        )

    auto_poster = AutoPoster(llm=llm, publish_fn=_publish_fn, notify_fn=_notify_fn)

    # step 7 — bot owns its dispatcher internally just hand it deps
    telegram_bot = TelegramBot(
        config=config,
        db=db,
        rag=rag,
        llm=llm,
        state=state,
        userbot=userbot,
        auto_poster=auto_poster,
    )

    # step 8 — fire both concurrently — if one dies the other keeps running
    await asyncio.gather(
        telegram_bot.start(),
        userbot.start(),
        return_exceptions=True,
    )


if __name__ == '__main__':
    asyncio.run(main())
