from aiogram import types
from aiogram.types import InputFile
from aiogram import Dispatcher
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
# parents[0] -> handlers
# parents[1] -> tgbot
# parents[2] -> корень проекта

async def about_us(message):
    file_path = BASE_DIR / "idk" / "canva tablet.pdf"

    await message.answer_document(
        InputFile(file_path),
        caption="⬆️ Yuqoridagi faylni bosing"
    )
def register_about_us(dp: Dispatcher):
    dp.register_message_handler(
        about_us,
        lambda m: m.text == "👉🏻 Biz haqimizda",
        state="*"
    )
