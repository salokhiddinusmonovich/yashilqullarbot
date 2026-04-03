from aiogram import types, Dispatcher 
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
async def shop_pass(message: types.Message):
    # Текст на узбекском, который звучит официально и вежливо
    text = (
        "<b>🙃 Sahifa tayyorlanmoqda</b>"
    )
    
    # Добавляем инлайн-кнопку, чтобы юзер мог вернуться или перейти в канал
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text="🔄 Asosiy menyu", callback_data="start_menu")) 
    # Если есть канал проекта, можно добавить ссылку на него:
    # kb.add(InlineKeyboardButton(text="📢 Yangiliklar", url="https://t.me/your_channel"))

    await message.answer(
        text, 
        parse_mode="HTML", 
        reply_markup=kb
    )


def register_shop(dp: Dispatcher):
    # Твои старые регистрации...
    dp.register_message_handler(shop_pass, text="🛍️ Eko-Shop", state="*")