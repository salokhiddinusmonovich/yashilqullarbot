from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.i18n import t
from tgbot.services.subscription import CHANNEL_URL


def subscription_keyboard():
    """«📢 Kanalga obuna boʻlish» + «✅ Obuna boʻldim» — на языке человека."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton(text=t("sub_btn_join"), url=CHANNEL_URL))
    keyboard.add(InlineKeyboardButton(text=t("sub_btn_check"), callback_data="check_subscription"))
    return keyboard
