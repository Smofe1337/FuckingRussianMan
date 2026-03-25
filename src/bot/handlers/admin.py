# admin panel — owner only inline button hell
# entry is /menu everything else is callbacks or forcereply
# touch this file and something will break i guarantee it

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.ai.llm import LLMEngine
from src.bot.i18n import get_strings
from src.bot.state import BotState
from src.config import Config
from src.storage.database import Database

log = logging.getLogger(__name__)

# autopost options in hours — add more if u want telegram to hate u
AUTOPOST_OPTIONS = [2.0, 4.0, 6.0, 12.0]


def make_admin_router(
    bot: Bot,
    llm: LLMEngine,
    db: Database,
    config: Config,
    userbot,        # Userbot | None — checked via is_connected property not ()
    auto_poster,    # AutoPoster — controls the bg posting loop
    state: BotState,
) -> Router:
    # builds and returns a router with all admin callbacks wired up
    router = Router()

    async def _publish(text: str, chat_id: int) -> None:
        # sends to channel — userbot if alive otherwise falls back to bot api
        state.own_posts.add(text)
        if userbot is not None and userbot.is_connected:
            await userbot.post(text)
        else:
            await bot.send_message(config.learn_channel, text)

    def _mode_display(s: dict) -> str:
        # translates internal mode string to whatever language the user speaks
        key = f'mode_name_{state.reply_mode}'
        return s.get(key, state.reply_mode)

    def _main_kb(s: dict) -> InlineKeyboardMarkup:
        # main menu keyboard — stats gen mode autopost post
        hours = auto_poster.interval_hours
        interval_label = s['autopost_off'] if hours == 0 else f'{hours:.0f}h'
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=s['stats_btn'], callback_data='admin:stats'),
                InlineKeyboardButton(text=s['gen_btn'],   callback_data='admin:gen'),
            ],
            [
                InlineKeyboardButton(
                    text=s['mode_btn'].format(mode=_mode_display(s)),
                    callback_data='admin:mode',
                ),
            ],
            [
                InlineKeyboardButton(
                    text=s['autopost_btn'].format(interval=interval_label),
                    callback_data='admin:autopost',
                ),
            ],
            [
                InlineKeyboardButton(text=s['post_btn'], callback_data='admin:post'),
            ],
        ])

    def _back_kb(s: dict) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=s['back_btn'], callback_data='admin:menu')],
        ])

    def _mode_kb(s: dict) -> InlineKeyboardMarkup:
        def lbl(key: str, val: str) -> str:
            return ('✓  ' if state.reply_mode == val else '      ') + s[key]

        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=lbl('mode_all',     'all'),     callback_data='admin:mode:all')],
            [InlineKeyboardButton(text=lbl('mode_mention', 'mention'), callback_data='admin:mode:mention')],
            [InlineKeyboardButton(text=lbl('mode_off',     'off'),     callback_data='admin:mode:off')],
            [InlineKeyboardButton(text=s['back_btn'],                  callback_data='admin:menu')],
        ])

    def _autopost_kb(s: dict) -> InlineKeyboardMarkup:
        # pairs of 2 options per row plus off and back at the bottom
        def lbl(h: float) -> str:
            mark = '✓  ' if auto_poster.interval_hours == h else '   '
            return f'{mark}{h:.0f}h'

        off_label = ('✓  ' if auto_poster.interval_hours == 0 else '   ') + s['autopost_off']
        pairs = [AUTOPOST_OPTIONS[i:i+2] for i in range(0, len(AUTOPOST_OPTIONS), 2)]
        rows  = [
            [InlineKeyboardButton(text=lbl(h), callback_data=f'admin:autopost:{int(h)}') for h in pair]
            for pair in pairs
        ]
        rows.append([InlineKeyboardButton(text=off_label, callback_data='admin:autopost:0')])
        rows.append([InlineKeyboardButton(text=s['back_btn'], callback_data='admin:menu')])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    def _gen_kb(s: dict) -> InlineKeyboardMarkup:
        # publish regen cancel — all u need for a draft review
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=s['gen_publish'],    callback_data='admin:gen:publish'),
                InlineKeyboardButton(text=s['gen_regenerate'], callback_data='admin:gen:regen'),
            ],
            [
                InlineKeyboardButton(text=s['gen_cancel'], callback_data='admin:menu'),
            ],
        ])

    # /menu — only way in for the owner

    @router.message(Command('menu'))
    async def cmd_menu(message: Message) -> None:
        # ignore anyone who isnt the owner — not their panel
        if message.from_user.id != config.owner_id:
            return
        lang = message.from_user.language_code
        state.lang = lang or 'en'
        s = get_strings(lang)
        await message.answer(s['menu_title'], reply_markup=_main_kb(s))

    @router.callback_query(F.data == 'admin:menu')
    async def cb_menu(cb: CallbackQuery) -> None:
        # re-renders the main menu in the same message
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.message.edit_text(s['menu_title'], reply_markup=_main_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:stats')
    async def cb_stats(cb: CallbackQuery) -> None:
        # shows how much the bot has eaten and what mode its in
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        s     = get_strings(state.lang)
        stats = db.stats()
        mode_label = _mode_display(s)
        text = (
            f'<b>{s["stats_title"]}</b>\n\n'
            f'{stats["total"]} сообщений\n'
            f'Режим - {mode_label}'
        )
        await cb.message.edit_text(text, reply_markup=_back_kb(s), parse_mode='HTML')
        await cb.answer()

    @router.callback_query(F.data == 'admin:gen')
    async def cb_gen(cb: CallbackQuery) -> None:
        # generate a post draft and shove it in pending_post
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.answer(s['gen_title'])
        await bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)

        state.pending_post = await asyncio.get_event_loop().run_in_executor(
            None, llm.generate_post, ''
        )

        await cb.message.edit_text(
            f'{s["gen_title"]}\n\n{state.pending_post}',
            reply_markup=_gen_kb(s),
        )

    @router.callback_query(F.data == 'admin:gen:regen')
    async def cb_gen_regen(cb: CallbackQuery) -> None:
        # throw away the current draft and cook a new one
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.answer(s['gen_title'])
        await bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)

        state.pending_post = await asyncio.get_event_loop().run_in_executor(
            None, llm.generate_post, ''
        )

        await cb.message.edit_text(
            f'{s["gen_title"]}\n\n{state.pending_post}',
            reply_markup=_gen_kb(s),
        )

    @router.callback_query(F.data == 'admin:gen:publish')
    async def cb_gen_publish(cb: CallbackQuery) -> None:
        # yeet the pending draft to channel and clear it
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        s = get_strings(state.lang)
        if not state.pending_post:
            await cb.answer('no pending post')
            return
        post = state.pending_post
        state.pending_post = ''
        await _publish(post, cb.message.chat.id)
        await cb.message.edit_text(s['post_published'], reply_markup=_back_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode')
    async def cb_mode(cb: CallbackQuery) -> None:
        # open the mode picker
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=_mode_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode:all')
    async def cb_mode_all(cb: CallbackQuery) -> None:
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        state.reply_mode = 'all'
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=_mode_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode:mention')
    async def cb_mode_mention(cb: CallbackQuery) -> None:
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        state.reply_mode = 'mention'
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=_mode_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:mode:off')
    async def cb_mode_off(cb: CallbackQuery) -> None:
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        state.reply_mode = 'off'
        s = get_strings(state.lang)
        await cb.message.edit_text(s['mode_title'], reply_markup=_mode_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:autopost')
    async def cb_autopost(cb: CallbackQuery) -> None:
        # open the autopost interval picker
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        s = get_strings(state.lang)
        await cb.message.edit_text(s['autopost_title'], reply_markup=_autopost_kb(s))
        await cb.answer()

    async def _set_autopost(cb: CallbackQuery, hours: float) -> None:
        # shared logic — set interval cancel old task fire new one
        if cb.from_user.id != config.owner_id:
            await cb.answer()
            return
        auto_poster.set_interval(hours)
        s = get_strings(state.lang)
        await cb.message.edit_text(s['autopost_title'], reply_markup=_autopost_kb(s))
        await cb.answer()

    @router.callback_query(F.data == 'admin:autopost:0')
    async def cb_autopost_off(cb: CallbackQuery) -> None:
        await _set_autopost(cb, 0)

    @router.callback_query(F.data == 'admin:autopost:2')
    async def cb_autopost_2h(cb: CallbackQuery) -> None:
        await _set_autopost(cb, 2.0)

    @router.callback_query(F.data == 'admin:autopost:4')
    async def cb_autopost_4h(cb: CallbackQuery) -> None:
        await _set_autopost(cb, 4.0)

    @router.callback_query(F.data == 'admin:autopost:6')
    async def cb_autopost_6h(cb: CallbackQuery) -> None:
        await _set_autopost(cb, 6.0)

    @router.callback_query(F.data == 'admin:autopost:12')
    async def cb_autopost_12h(cb: CallbackQuery) -> None:
        await _set_autopost(cb, 12.0)

    @router.callback_query(F.data == 'admin:post')
    async def cb_post(cb: CallbackQuery) -> None:
        # send forcereply prompt so owner types the post text directly in chat
        if cb.from_user.id != config.owner_id:
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
        # owner replied to the forcereply prompt — grab text and send it to channel
        if message.from_user.id != config.owner_id:
            return
        if not message.reply_to_message:
            return
        s    = get_strings(state.lang)
        text = (message.text or '').strip()
        if not text:
            return
        await _publish(text, message.chat.id)
        await message.reply(s['post_published'])

    return router
