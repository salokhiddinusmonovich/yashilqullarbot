from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from asgiref.sync import sync_to_async

from ..keyboards import reply
from .qr_handler import process_qr_logic
from .feedback import ask_feedback

async def user_start(message: Message, state: FSMContext):
    from app_telegram.models import TGUser, LoginToken

    await state.finish()

    args = message.get_args()

    # --- LOGIN VIA WEBSITE (deep-link) ---
    if args and args.startswith('login_'):
        token = args.replace('login_', '')
        tg_id = message.from_user.id
        fullname = message.from_user.full_name

        user, created = await sync_to_async(TGUser.objects.get_or_create)(
            tg_id=tg_id,
            defaults={
                'fullname': fullname,
                'username': message.from_user.username or '',
                'email': '',
                'phone': '',
            }
        )
        if not created:
            user.fullname = fullname
            if message.from_user.username:
                user.username = message.from_user.username
            await sync_to_async(user.save)(update_fields=['fullname', 'username'])

        updated = await sync_to_async(
            LoginToken.objects.filter(token=token, status='pending').update
        )(status='confirmed', tg_id=tg_id)

        if updated:
            await message.answer(
                "✅ <b>Вход подтверждён!</b>\n\nВернись на вкладку с сайтом — ты уже в аккаунте.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "⚠️ Ссылка для входа устарела или уже использована.\n"
                "Вернись на сайт и попробуй войти ещё раз."
            )
        return

    # --- QR CODE SCANNING VIA DEEP LINK ---
    if args and args.startswith('qr_'):
        raw_target_id = args.replace('qr_', '')

        try:
            target_id = int(raw_target_id)
        except ValueError:
            await message.answer("❌ Malumotlar formati noto'g'ri (ID raqam bo'lishi kerak).")
            return

        # process_qr_logic теперь возвращает ещё и project —
        # он нужен ниже, чтобы запустить опрос обратной связи
        result_text, volunteer, project = await process_qr_logic(message.from_user.id, target_id)

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

            # Сразу следом — запрашиваем обратную связь по мероприятию
            if project:
                try:
                    await ask_feedback(message.bot, volunteer.tg_id, project.id, project.title)
                except Exception:
                    pass  # не критично, если не получилось отправить опрос
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