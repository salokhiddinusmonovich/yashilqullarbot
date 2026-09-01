"""
Единый список текстов всех reply-кнопок бота.

Нужен там, где хендлер ждёт свободный текст в FSM-состоянии (комментарий
к фидбеку, email при регистрации и т.п.) — если юзер вместо ответа тыкает
обычную кнопку меню, это ТОЖЕ приходит как обычное текстовое сообщение,
и без проверки оно молча сохраняется как будто это был реальный ответ,
а сама кнопка "не срабатывает".

Если добавляешь новую reply-кнопку где-то в tgbot/ — добавь её текст и сюда.
"""

KNOWN_MENU_BUTTON_TEXTS = frozenset({
    "🌟 Biz haqimizda",
    "🤝 Hamkorlarimiz",
    "🚀 Loyihaga qo‘shilish",
    "👤 Mening profilim",
    "🌿 Mening QR-kodim",
    "⬅️ Orqaga",
    "🌱 Tadbirlar",
    "📅 Kelgusi tadbirlar",
    "📜 O'tgan tadbirlar",
    "✅ Ro'yxatdan o'tish",
    "📄 Profilni ko'rish",
    "📸 Rasmni yangilash",
    "✍️ Ismni o'zgartirish",
    "📍 Hududni o'zgartirish",
    "📱 Raqamni yuborish",
})


def is_menu_button_text(text: str) -> bool:
    return bool(text) and text.strip() in KNOWN_MENU_BUTTON_TEXTS
