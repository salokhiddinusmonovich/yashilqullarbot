from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from asgiref.sync import sync_to_async

from app_telegram.models import TGUser
from ..keyboards import reply
from .qr_handler import process_qr_logic

async def user_start(message: Message, state: FSMContext):
    await state.finish()

    # --- ПРОВЕРКА НА СКАНЕР (Deep Link) ---
    args = message.get_args()
    if args and args.startswith('qr_'):
        target_id = args.replace('qr_', '')
        
        # РАСПАКОВКА: получаем текст и объект отдельно
        result_text, volunteer = await process_qr_logic(message.from_user.id, target_id)

        # Отправляем только текст (избегаем ошибки CantParseEntities)
        await message.answer(result_text, parse_mode="HTML")

        # Отправляем уведомление волонтеру, если всё ок
        if volunteer and "✅" in result_text:
            try:
                await message.bot.send_message(
                    chat_id=volunteer.tg_id,
                    text=(
                        f"🌟 <b>Tadbirda ishtirok etganingiz tasdiqlandi!</b>\n\n"
                        f"Sizga 10 ball berildi. Hozirgi balansingiz: <b>{volunteer.balance} ball</b>.\n"
                        f"Rahmat, tabiat himoyachisi! 🌿"
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass 
        return

    # --- ОБЫЧНОЕ ПРИВЕТСТВИЕ ---
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()

    if user:
        await message.answer(
            f"👋 Salom, {hbold(user.fullname)}! @YashilQollar oilasiga xush kelibsiz.", 
            reply_markup=reply.hi_there(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"👋 Salom, {hbold(message.from_user.full_name)}! @YashilQollar oilasiga xush kelibsiz.", 
            reply_markup=reply.auth_btn(),
            parse_mode="HTML"
        )

def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")