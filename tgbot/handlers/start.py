from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from asgiref.sync import sync_to_async

from ..keyboards import reply
from .qr_handler import process_qr_logic

async def user_start(message: Message, state: FSMContext):
    from app_telegram.models import TGUser
    
    await state.finish()

    # --- QR CODE SCANNING VIA DEEP LINK ---
    args = message.get_args()
    if args and args.startswith('qr_'):
        raw_target_id = args.replace('qr_', '')
        
        # Safety catch: Ensure the target ID is actually a valid number
        try:
            target_id = int(raw_target_id)
        except ValueError:
            await message.answer("❌ Malumotlar formati noto'g'ri (ID raqam bo'lishi kerak).")
            return
        
        # UNPACKING: passes scanner_tg_id and target_tg_id safely
        result_text, volunteer = await process_qr_logic(message.from_user.id, target_id)

        # Send response back to the scanning staff member
        await message.answer(result_text, parse_mode="HTML")

        # Notify the volunteer if attendance was successfully recorded
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
                pass  # Avoid halting execution if the volunteer blocked the bot
        return

    # --- STANDARD GREETING FLOW ---
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