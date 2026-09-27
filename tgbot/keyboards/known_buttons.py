"""
Тексты всех reply-кнопок бота на всех языках.

Нужен там, где хендлер ждёт свободный текст в FSM-состоянии (комментарий
к фидбеку, email при регистрации и т.п.) — если юзер вместо ответа тыкает
обычную кнопку меню, это ТОЖЕ приходит как обычное текстовое сообщение,
и без проверки оно молча сохраняется как будто это был реальный ответ.

Если добавляешь новую reply-кнопку — добавь её ключ сюда.
"""
from tgbot.i18n import variants, LANG_BUTTON

_BUTTON_KEYS = (
    "btn_about", "btn_join", "btn_qr", "btn_guide", "btn_profile", "btn_events", "btn_admin",
    "btn_back", "btn_register", "btn_phone", "btn_partners", "btn_upcoming", "btn_past",
    "btn_event_register", "btn_view_profile", "btn_change_photo", "btn_change_name",
    "btn_change_region", "btn_shop", "btn_invite", "btn_spot", "spot_btn_cancel",
)

KNOWN_MENU_BUTTON_TEXTS = frozenset(
    [text for key in _BUTTON_KEYS for text in variants(key)] + [LANG_BUTTON]
)


def is_menu_button_text(text: str) -> bool:
    return bool(text) and text.strip() in KNOWN_MENU_BUTTON_TEXTS
