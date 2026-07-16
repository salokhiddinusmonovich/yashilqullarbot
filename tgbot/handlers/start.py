from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from asgiref.sync import sync_to_async

from ..keyboards import reply
from .qr_handler import process_qr_logic
from .feedback import ask_feedback
from .link_account import ask_if_registered  # НОВОЕ

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
        if not created:  # ← БЫЛО "if not created:not created:" — синтаксическая ошибка, исправлено
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

        result_text, volunteer, project = await process_qr_logic(message.from_user.id, target_id)

        await message.answer(result_text, parse_mode="HTML")

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

            if project:
                try:
                    await ask_feedback(message.bot, volunteer.tg_id, project.id, project.title)
                except Exception:
                    pass
        return

    # --- STANDARD GREETING FLOW ---
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()

    if user:
        # Уже зарегистрирован (есть tg_id в базе) — обычное приветствие, без изменений
        await message.answer(
            f"👋 Salom, {hbold(user.fullname)}! @YashilQollar oilasiga xush kelibsiz.",
            reply_markup=reply.hi_there(),
            parse_mode="HTML"
        )
    else:
        # ИЗМЕНЕНО: раньше здесь сразу показывался reply.auth_btn().
        # Теперь СНАЧАЛА спрашиваем "уже есть аккаунт на сайте?" —
        # старая кнопка auth_btn() показывается только если юзер ответит
        # "нет, впервые" (см. process_choice в link_account.py).
        await ask_if_registered(message)

def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")