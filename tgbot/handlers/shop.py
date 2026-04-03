from aiogram import types, Dispatcher 
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
async def shop_pass(message: types.Message):
    # Текст на узбекском, который звучит официально и вежливо
    text = (
        "<b>🙃 Sahifa tayyorlanmoqda</b>"
    )
  

    await message.answer(
        text, 
        parse_mode="HTML", 
    )


def register_shop(dp: Dispatcher):
    # Твои старые регистрации...
    dp.register_message_handler(shop_pass, text="🛍️ Eko-Shop", state="*")