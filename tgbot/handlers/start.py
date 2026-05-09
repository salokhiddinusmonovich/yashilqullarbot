from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from tgbot.models.commands import add_or_create_user
from  ..keyboards import reply
from aiogram.utils.markdown import hbold
from app_telegram.models import TGUser
from asgiref.sync import sync_to_async
from .qr_handler import process_qr_logic, send_user_qr

async def user_start(message: Message, state: FSMContext):
    await state.finish()

    # --- ПРОВЕРКА НА СКАНЕР (Deep Link) ---
    args = message.get_args() # В aiogram 2.x аргументы берутся так
    if args and args.startswith('qr_'):
        target_id = args.replace('qr_', '')
        # Здесь вызываем логику проверки (process_qr_logic)
        # ВАЖНО: импортируй process_qr_logic из qr_handler.py
        result_text = await process_qr_logic(message.from_user.id, target_id)
        await message.answer(result_text, parse_mode="HTML")
        return # Выходим, чтобы не показывать приветствие

    # --- ТВОЯ ОБЫЧНАЯ ЛОГИКА ---
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()

    if user:
        await message.answer(
            f"👋 Salom, {hbold(user.fullname)}! @YashilQollar oilasiga xush kelibsiz.", 
            reply_markup=reply.hi_there()
        )
    else:
        await message.answer(
            f"👋 Salom, {hbold(message.from_user.full_name)}! @YashilQollar oilasiga xush kelibsiz.", 
            reply_markup=reply.auth_btn()
        )


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
