# telegrambot — plugs all the routers together and kicks off polling
# dependency injection only no globals touch a global and u lose

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, ErrorEvent

from src.ai.llm import LLMEngine
from src.ai.rag import RAGIndex
from src.bot.handlers.channel import make_channel_router
from src.bot.handlers.chat import make_chat_router
from src.bot.handlers.admin import make_admin_router
from src.bot.state import BotState
from src.config import Config
from src.scheduler.autopost import AutoPoster
from src.storage.database import Database

log = logging.getLogger(__name__)


class TelegramBot:
    # owns aiogram bot + dispatcher — all deps injected nothing hardcoded
    # if u need to add a router just shove it in _register_routers

    def __init__(
        self,
        config: Config,
        db: Database,
        rag: RAGIndex,
        llm: LLMEngine,
        state: BotState,
        userbot,       # Userbot | None — optional userbot for publishing
        auto_poster: AutoPoster,
    ) -> None:
        self._config      = config
        self._db          = db
        self._rag         = rag
        self._llm         = llm
        self._state       = state
        self._userbot     = userbot
        self._auto_poster = auto_poster

        self._bot = Bot(token=config.bot_token)
        self._dp  = Dispatcher()

        self._register_error_handler()
        self._register_routers()

    def _register_error_handler(self) -> None:
        # catches every unhandled exception and dms the owner — beats silent failures
        bot_ref  = self._bot
        owner_id = self._config.owner_id

        @self._dp.errors()
        async def on_error(event: ErrorEvent) -> None:
            exc      = event.exception
            err_type = type(exc).__name__
            err_msg  = str(exc)[:200]
            try:
                await bot_ref.send_message(
                    owner_id,
                    f'⚠️ Bot error\n\n{err_type}  {err_msg}',
                )
            except Exception:
                pass
            log.error('unhandled update error: %s: %s', err_type, err_msg)

    def _register_routers(self) -> None:
        # wire all routers — order matters admin first so /menu doesnt get eaten by chat
        self._dp.include_router(
            make_admin_router(
                bot=self._bot,
                llm=self._llm,
                db=self._db,
                config=self._config,
                userbot=self._userbot,
                auto_poster=self._auto_poster,
                state=self._state,
            )
        )
        self._dp.include_router(
            make_chat_router(
                bot=self._bot,
                llm=self._llm,
                state=self._state,
                config=self._config,
            )
        )
        self._dp.include_router(
            make_channel_router(
                db=self._db,
                rag=self._rag,
                state=self._state,
                config=self._config,
            )
        )

    async def _build_rag_bg(self) -> None:
        # rag index builds in bg — dont block startup waiting for this fat thing
        log.info('rag -> background indexing started')
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._rag.build_index)
            log.info('rag -> index ready')
        except Exception as e:
            log.warning('rag -> indexing failed: %s (falling back to random examples)', e)

    async def start(self) -> None:
        # boots everything up — ollama check rag bg task commands autoposter then polling
        loop = asyncio.get_event_loop()
        ok   = await loop.run_in_executor(None, self._llm.check_ollama)
        if not ok:
            log.warning("ollama not found or model '%s' not installed", self._config.ollama_model)
        else:
            log.info('ollama -> model %s is up', self._config.ollama_model)

        # register /menu in telegram ui — one command thats all we need
        await self._bot.set_my_commands([
            BotCommand(command='menu', description='Open admin panel'),
            BotCommand(command='gen',  description='Generate post — /gen <topic>'),
        ])

        # rag in bg so bot starts instantly without waiting for chroma to wake up
        asyncio.create_task(self._build_rag_bg())

        # start autoposter — if interval is 0 it just sits there doing nothing
        self._auto_poster.start(self._config.auto_post_hours)
        if self._config.auto_post_hours > 0:
            log.info('autopost -> every %.1f h', self._config.auto_post_hours)

        log.info(
            'bot started — chat: %s | mode: %s',
            self._config.target_chat,
            self._state.reply_mode,
        )

        await self._dp.start_polling(
            self._bot,
            allowed_updates=['message', 'channel_post', 'callback_query'],
        )
