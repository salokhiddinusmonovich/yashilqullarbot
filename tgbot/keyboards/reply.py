from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from .text import register_text, phone_text
# from app_telegram.models import TGUser

guide_text = "❓ Qo'llanma"
admin_panel_text = "🛠 Admin panel"


def hi_there(is_admin: bool = False):
    keyboard = [
        # Запятая в конце каждой строки ряда обязательна!
        [KeyboardButton(text="🌟 Biz haqimizda"), KeyboardButton(text="🚀 Loyihaga qo‘shilish")],
        [KeyboardButton(text="🌿 Mening QR-kodim"), KeyboardButton(text=guide_text)],
        [KeyboardButton(text="👤 Mening profilim")],
        [KeyboardButton(text="🌱 Tadbirlar")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=admin_panel_text)])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def auth_btn():
    register_btn = KeyboardButton(text=register_text)
    return ReplyKeyboardMarkup(keyboard=[[register_btn]],resize_keyboard=True,  one_time_keyboard=True)

def contact_btn():
    phone = KeyboardButton(text=phone_text, request_contact=True)
    return ReplyKeyboardMarkup(keyboard=[[phone]], resize_keyboard=True, one_time_keyboard=True)


async def main_menu(tg_id: int):
    """Главное меню с кнопкой админки для тех, у кого is_admin."""
    from asgiref.sync import sync_to_async
    from app_telegram.models import TGUser
    is_admin = await sync_to_async(TGUser.objects.filter(tg_id=tg_id, is_admin=True).exists)()
    return hi_there(is_admin)
