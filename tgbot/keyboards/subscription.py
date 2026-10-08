from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


CHANNEL_USERNAME = "@yashilqollar"
CHANNEL_URL = "https://t.me/yashilqollar"


def subscription_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)

    keyboard.add(
        InlineKeyboardButton(
            text="📢 Подписаться на канал",
            url=CHANNEL_URL
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            text="✅ Я подписался",
            callback_data="check_subscription"
        )
    )

    return keyboard