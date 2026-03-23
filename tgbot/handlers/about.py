from aiogram import types
from aiogram.types import InputFile
from aiogram import Dispatcher
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
# parents[0] -> handlers
# parents[1] -> tgbot
# parents[2] -> корень проекта

async def about_us(message):
    # Fayl yo'lini ko'rsatamiz
    file_path = BASE_DIR / "idk" / "poster.png"

    # answer_photo orqali rasm sifatida yuboramiz
    await message.answer_photo(
        photo=InputFile(file_path),
        caption="🌱 Biz haqimizda ma'lumotlar bilan tanishing."
    )

def register_about_us(dp: Dispatcher):
    dp.register_message_handler(
        about_us,
        lambda m: m.text == "🌟 Biz haqimizda",
        state="*"
    )