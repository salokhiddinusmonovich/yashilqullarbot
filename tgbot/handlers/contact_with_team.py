from aiogram import Dispatcher
from aiogram.types import Message

# 1. Tugma bosilganda ishlaydigan funksiya
async def join_project(message: Message):
    text = (
        "🌱 <b>Barqaror kelajak uchun!</b>\n\n"
        "✨ Taklif yoki savollaringiz bormi?\n"
        "👥 Jamoamizga qo‘shilishni xohlaysizmi?\n"
        "📩 Unda <b>@yashilqollar_admin</b> ga yozing\n\n"
        "🤝 Hamkorlik bo‘yicha:\n"
        "📩 <b>@abdulboriyw</b> ga murojaat qiling"
    )
    await message.answer(text)

# 2. Uni handler sifatida ro'yxatdan o'tkazish
def register_project_handlers(dp: Dispatcher):
    # Bu yerda matnli filtr orqali "🚀 Loyihaga qo‘shilish" tugmasini tutib olamiz
    dp.register_message_handler(join_project, text="🚀 Loyihaga qo‘shilish", state="*")