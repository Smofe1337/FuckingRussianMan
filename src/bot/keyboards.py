# all inline keyboard builders live here — import from here never build inline keyboards elsewhere

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src import settings


def _interval_label(hours: float) -> str:
    # < 1h shows as minutes — >= 1h shows as hours
    if hours == 0:
        return 'off'
    mins = round(hours * 60)
    if mins < 60:
        return f'{mins}min'
    return f'{int(hours)}h'


def _hours_to_cb(hours: float) -> str:
    # encode as integer minutes in callback so no floats in callback_data
    return f'admin:autopost:{round(hours * 60)}'


def main_kb(s: dict, mode_label: str, interval_hours: float) -> InlineKeyboardMarkup:
    interval_label = s['autopost_off'] if interval_hours == 0 else _interval_label(interval_hours)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=s['stats_btn'], callback_data='admin:stats'),
            InlineKeyboardButton(text=s['gen_btn'],   callback_data='admin:gen'),
        ],
        [
            InlineKeyboardButton(
                text=s['mode_btn'].format(mode=mode_label),
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


def back_kb(s: dict) -> InlineKeyboardMarkup:
    # single back button — used on every sub-page
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s['back_btn'], callback_data='admin:menu')],
    ])


def mode_kb(s: dict, current_mode: str) -> InlineKeyboardMarkup:
    # one mode per row — russian text gets truncated in one row dont even try
    def lbl(key: str, val: str) -> str:
        return ('✓  ' if current_mode == val else '      ') + s[key]

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=lbl('mode_all',     'all'),     callback_data='admin:mode:all')],
        [InlineKeyboardButton(text=lbl('mode_mention', 'mention'), callback_data='admin:mode:mention')],
        [InlineKeyboardButton(text=lbl('mode_off',     'off'),     callback_data='admin:mode:off')],
        [InlineKeyboardButton(text=s['back_btn'],                  callback_data='admin:menu')],
    ])


def autopost_kb(s: dict, current_hours: float) -> InlineKeyboardMarkup:
    # 3 options per row — off and back at the bottom
    def lbl(h: float) -> str:
        mark = '✓  ' if current_hours == h else '   '
        return mark + _interval_label(h)

    off_label = ('✓  ' if current_hours == 0 else '   ') + s['autopost_off']
    pairs = [settings.AUTOPOST_OPTIONS[i:i+3] for i in range(0, len(settings.AUTOPOST_OPTIONS), 3)]
    rows  = [
        [InlineKeyboardButton(text=lbl(h), callback_data=_hours_to_cb(h)) for h in pair]
        for pair in pairs
    ]
    rows.append([InlineKeyboardButton(text=off_label, callback_data='admin:autopost:0')])
    rows.append([InlineKeyboardButton(text=s['back_btn'], callback_data='admin:menu')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gen_kb(s: dict) -> InlineKeyboardMarkup:
    # draft review — publish regen cancel
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=s['gen_publish'],    callback_data='admin:gen:publish'),
            InlineKeyboardButton(text=s['gen_regenerate'], callback_data='admin:gen:regen'),
        ],
        [
            InlineKeyboardButton(text=s['gen_cancel'], callback_data='admin:menu'),
        ],
    ])
