# admin panel — owner only
# /menu opens the panel /gen <topic> generates a post inline
# keyboards live in src/bot/keyboards.py — dont build inline markup here

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ForceReply, Message

from src.ai.llm import LLMEngine
from src.bot.i18n import get_strings
from src.bot.keyboards import (
    autopost_kb,
    back_kb,
    gen_kb,
    main_kb,
    mode_kb,
)
from src.bot.state import BotState
from src.config import Config
from src.storage.database import Database

log = logging.getLogger(__name__)


def make_admin_router(
    bot: Bot,
    llm: LLMEngine,
    db: Database,
    config: Config,
    userbot,
    auto_poster,
    state: BotState,
) -> Router:
    router = Router()

    # helpers

    async def _publish(text: str) -> None:
        # channel via userbot if alive — bot api as fallback
        state.own_posts.add(text)
        if userbot is not None and userbot.is_connected:
            await userbot.post(text)
        else:
            await bot.send_message(config.learn_channel, text)

    def _mode_label(s: dict) -> str:
        return s.get(f'mode_name_{state.reply_mode}', state.reply_mode)

    async def _generate(topic: str = '') -> str:
        # runs llm in executor — doesnt block the event loop
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, llm.generate_post, topic)

    def _owner(user_id: int) -> bool:
        return user_id == config.owner_id

    # /menu

    @router.message(Command('menu'))
    async def cmd_menu(message: Message) -> None:
        if not _owner(message.from_user.id):
            return
        state.lang = message.from_user.language_code or 'en'
        s = get_strings(state.lang)
        await message.answer(
            s['menu_title'],
            reply_markup=main_kb(s, _mode_label(s), auto_poster.interval_hours),
        )

    # /gen <topic> — generates a post on the given topic with inline buttons

    @router.message(Command('gen'))
    async def cmd_gen(message: Message) -> None:
        if not _owner(message.from_user.id):
            return
        s = get_strings(state.lang)
        topic = (message.text or '').split(maxsplit=1)
        topic = topic[1].strip() if len(topic) > 1 else ''
        if not topic:
            await message.answer(s['gen_usage'])
            return

        await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        state.pending_post = await _generate(topic)
        await message.answer(
            f'{s["gen_title"]}\n\n{state.pending_post}',
            reply_markup=gen_kb(s),
        )

    # callbacks

    @router.callback_query(F.data == 'admin:menu')
    async def cb_menu(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.message.edit_text(
            s['menu_title'],
            reply_markup=main_kb(s, _mode_label(s), auto_poster.interval_hours),
        )
        await cb.answer()

    @router.callback_query(F.data == 'admin:stats')
    async def cb_stats(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s     = get_strings(state.lang)
        stats = await db.stats()
        text  = (
            f'<b>{s["stats_title"]}</b>\n\n'
            f'{stats["total"]} сообщений\n'
            f'Режим - {_mode_label(s)}'
        )
        await cb.message.edit_text(text, reply_markup=back_kb(s), parse_mode='HTML')
        await cb.answer()

    @router.callback_query(F.data == 'admin:gen')
    async def cb_gen(cb: CallbackQuery) -> None:
        # generate from menu without topic
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.answer(s['gen_title'])
        await bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)
        state.pending_post = await _generate()
        await cb.message.edit_text(
            f'{s["gen_title"]}\n\n{state.pending_post}',
            reply_markup=gen_kb(s),
        )

    @router.callback_query(F.data == 'admin:gen:regen')
    async def cb_gen_regen(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.answer(s['gen_title'])
        await bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)
        state.pending_post = await _generate()
        await cb.message.edit_text(
            f'{s["gen_title"]}\n\n{state.pending_post}',
            reply_markup=gen_kb(s),
        )

    @router.callback_query(F.data == 'admin:gen:publish')
    async def cb_gen_publish(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s = get_strings(state.lang)
        if not state.pending_post:
            await cb.answer('no pending post')
            return
        post = state.pending_post
        state.pending_post = ''
        await _publish(post)
        await cb.message.edit_text(s['post_published'], reply_markup=back_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode')
    async def cb_mode(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=mode_kb(s, state.reply_mode))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode:all')
    async def cb_mode_all(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        state.reply_mode = 'all'
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=mode_kb(s, state.reply_mode))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode:mention')
    async def cb_mode_mention(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        state.reply_mode = 'mention'
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=mode_kb(s, state.reply_mode))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode:off')
    async def cb_mode_off(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        state.reply_mode = 'off'
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=mode_kb(s, state.reply_mode))
        await cb.answer()

    @router.callback_query(F.data == 'admin:autopost')
    async def cb_autopost(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.message.edit_text(s['autopost_title'], reply_markup=autopost_kb(s, auto_poster.interval_hours))
        await cb.answer()

    @router.callback_query(F.data.startswith('admin:autopost:'))
    async def cb_autopost_set(cb: CallbackQuery) -> None:
        # single handler for all interval options — parses minutes from callback_data
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        minutes = int(cb.data.split(':')[2])
        auto_poster.set_interval(minutes / 60)
        s = get_strings(state.lang)
        await cb.message.edit_text(s['autopost_title'], reply_markup=autopost_kb(s, auto_poster.interval_hours))
        await cb.answer()

    @router.callback_query(F.data == 'admin:post')
    async def cb_post(cb: CallbackQuery) -> None:
        if not _owner(cb.from_user.id):
            await cb.answer()
            return
        s = get_strings(state.lang)
        await bot.send_message(
            cb.message.chat.id,
            s['post_title'],
            reply_markup=ForceReply(selective=True),
        )
        await cb.answer()

    @router.message(F.reply_to_message & F.reply_to_message.from_user.is_bot)
    async def handle_post_reply(message: Message) -> None:
        # owner replied to forcereply — publish the text
        if not _owner(message.from_user.id):
            return
        if not message.reply_to_message:
            return
        s    = get_strings(state.lang)
        text = (message.text or '').strip()
        if not text:
            return
        await _publish(text)
        await message.reply(s['post_published'])

    return router
