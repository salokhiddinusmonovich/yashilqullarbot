from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app_telegram.models import TGUser

def region_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    for value, label in TGUser.Region.choices:
        callback_data = f"region:{value}"  # это безопасно, <64 символов
        kb.insert(InlineKeyboardButton(text=label, callback_data=callback_data))
    return kb
