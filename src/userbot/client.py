# userbot — telethon client acting as the real account
# learns from channel learns from chats replies as u — whole package
# if api creds are missing it just skips silently nobody cares

import asyncio
import logging
import random
from typing import Optional

from telethon import TelegramClient, events
from telethon.tl.types import User

from src.ai.llm import LLMEngine
from src.config import Config
from src.storage.database import Database

log = logging.getLogger(__name__)


class Userbot:
    # wraps telethon — all deps injected no globals
    # communicates with the rest of the app via asyncio queue

    def __init__(
        self,
        db: Database,
        llm: LLMEngine,
        config: Config,
    ) -> None:
        self._db     = db
        self._llm    = llm
        self._config = config

        self._client: Optional[TelegramClient] = None
        # bot pushes post tasks here — userbot drains it in _handle_tasks
        self._task_queue: asyncio.Queue = asyncio.Queue()

    @property
    def is_connected(self) -> bool:
        # property not method — calling it with () will make u look dumb
        return self._client is not None and self._client.is_connected()

    async def post(self, text: str) -> None:
        # enqueue a post — actual send happens in _handle_tasks loop
        await self._task_queue.put({'action': 'post', 'text': text})

    async def _delay_typing(
        self, chat_id: int, text: str, reply_to_msg_id: int
    ) -> None:
        # shows typing for a random duration before sending — fools everyone
        delay = random.uniform(4, 15)
        async with self._client.action(chat_id, 'typing'):
            await asyncio.sleep(delay)
        await self._client.send_message(chat_id, text, reply_to=reply_to_msg_id)

    async def _handle_tasks(self) -> None:
        # drains the queue forever — currently only handles post action
        while True:
            task = await self._task_queue.get()
            try:
                if task['action'] == 'post':
                    await self._client.send_message(
                        self._config.learn_channel, task['text']
                    )
                    log.info('userbot published to channel -> %s…', task['text'][:60])
            except Exception as e:
                log.error('userbot task error -> %s', e)
            finally:
                self._task_queue.task_done()

    async def start(self) -> None:
        # connects telethon registers listeners and runs until disconnected
        # bails early if api creds arent set — no crash just a warning
        if not self._config.tg_api_id or not self._config.tg_api_hash:
            log.warning('TG_API_ID / TG_API_HASH not set — userbot disabled')
            return

        self._client = TelegramClient(
            'userbot.session',
            self._config.tg_api_id,
            self._config.tg_api_hash,
        )
        await self._client.start()

        me = await self._client.get_me()
        log.info('userbot started as -> %s (@%s)', me.first_name, me.username)

        # learn from every post in learn_channel
        @self._client.on(events.NewMessage(chats=self._config.learn_channel))
        async def on_channel_post(event: events.NewMessage.Event) -> None:
            text = event.raw_text or ''
            if len(text) > 15:
                self._db.save_learned(text.strip(), source='channel_userbot')
                log.info('userbot learned from channel -> %s…', text[:60])

        # reply in userbot_chats as the real account
        if self._config.userbot_chats:
            @self._client.on(
                events.NewMessage(chats=self._config.userbot_chats, incoming=True)
            )
            async def on_userbot_chat(event: events.NewMessage.Event) -> None:
                # skip own messages so we dont reply to ourselves forever
                sender = await event.get_sender()
                if isinstance(sender, User) and sender.is_self:
                    return

                text = event.raw_text or ''
                if not text:
                    return

                response = await asyncio.get_event_loop().run_in_executor(
                    None, self._llm.generate, text
                )
                if response:
                    await self._delay_typing(event.chat_id, response, event.message.id)

        # task queue runs in bg — doesnt block the event listener
        asyncio.create_task(self._handle_tasks())

        log.info(
            'userbot listening -> channel %s | chats %s',
            self._config.learn_channel,
            self._config.userbot_chats or 'none configured',
        )

        await self._client.run_until_disconnected()
