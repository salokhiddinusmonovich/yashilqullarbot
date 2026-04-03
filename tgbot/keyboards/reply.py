from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from .text import register_text, phone_text
from app_telegram.models import TGUser

def hi_there():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Mening profilim"), KeyboardButton(text="🛍️ Eko-Shop")],
            [KeyboardButton(text="🌟 Biz haqimizda"), KeyboardButton(text="🚀 Loyihaga qo‘shilish")],
            [KeyboardButton(text="🌱 Tadbirlar")],

            
        ],
        resize_keyboard=True  # чтобы кнопки были компактные
    )


def auth_btn():
    register_btn = KeyboardButton(text=register_text)
    return ReplyKeyboardMarkup(keyboard=[[register_btn]],resize_keyboard=True,  one_time_keyboard=True)

def contact_btn():
    phone = KeyboardButton(text=phone_text, request_contact=True)
    return ReplyKeyboardMarkup(keyboard=[[phone]], resize_keyboard=True, one_time_keyboard=True)


