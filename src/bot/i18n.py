# i18n — two dicts ru and en thats it no fancy library needed
# auto-detects from message.from_user.language_code — starts with ru → RU else EN

RU = {
    'menu_title':        '⚙ Панель управления',
    'stats_btn':         'Статистика',
    'gen_btn':           'Создать пост',
    'mode_btn':          'Режим — {mode}',
    'autopost_btn':      'Автопост — {interval}',
    'post_btn':          'Пост в канал',
    'back_btn':          '← Назад',
    'mode_title':        'Выбери режим ответов',
    'mode_all':          'Все сообщения',
    'mode_mention':      'Упоминания',
    'mode_off':          'Выключить',
    'autopost_title':    'Интервал автопостинга',
    'autopost_off':      'Выключить',
    'gen_title':         'Черновик поста',
    'gen_publish':       'Опубликовать',
    'gen_regenerate':    'Перегенерировать',
    'gen_cancel':        'Отмена',
    'gen_usage':         'Использование: /gen <тема>',
    'post_title':        'Отправь текст для публикации в канал',
    'post_published':    'Опубликовано',
    'stats_title':       'База знаний',
    'mode_name_all':     'все',
    'mode_name_mention': 'упоминания',
    'mode_name_off':     'выкл',
}

EN = {
    'menu_title':        '⚙ Admin panel',
    'stats_btn':         'Stats',
    'gen_btn':           'Generate post',
    'mode_btn':          'Mode — {mode}',
    'autopost_btn':      'Auto-post — {interval}',
    'post_btn':          'Post to channel',
    'back_btn':          '← Back',
    'mode_title':        'Select reply mode',
    'mode_all':          'All messages',
    'mode_mention':      'Mentions only',
    'mode_off':          'Disable',
    'autopost_title':    'Auto-post interval',
    'autopost_off':      'Disable',
    'gen_title':         'Post draft',
    'gen_publish':       'Publish',
    'gen_regenerate':    'Regenerate',
    'gen_cancel':        'Cancel',
    'gen_usage':         'Usage: /gen <topic>',
    'post_title':        'Send the text to publish to channel',
    'post_published':    'Published',
    'stats_title':       'Knowledge base',
    'mode_name_all':     'all',
    'mode_name_mention': 'mention',
    'mode_name_off':     'off',
}


def get_strings(language_code: str) -> dict:
    # ru if starts with ru — anything else gets english
    if language_code and language_code.lower().startswith('ru'):
        return RU
    return EN
