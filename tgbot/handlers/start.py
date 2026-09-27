from html import escape

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from asgiref.sync import sync_to_async

from tgbot.i18n import t
from tgbot.services.lang import lang_of
from ..keyboards import reply
from .qr_handler import process_qr_logic
from .feedback import ask_feedback
from .link_account import ask_if_registered
from .language import ask_language


async def user_start(message: Message, state: FSMContext, lang: str = None):
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
                'email': None,
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

        await message.answer(t("login_confirmed") if updated else t("login_expired"))
        return

    # --- QR CODE SCANNING VIA DEEP LINK ---
    if args and args.startswith('qr_'):
        try:
            target_id = int(args.replace('qr_', ''))
        except ValueError:
            await message.answer(t("qr_bad_format"))
            return

        result_text, volunteer, project, confirmed = await process_qr_logic(message.from_user.id, target_id)
        await message.answer(result_text)

        if confirmed:
            # уведомление — на языке волонтёра, а не координатора
            v_lang = await lang_of(volunteer.tg_id)
            try:
                await message.bot.send_message(
                    chat_id=volunteer.tg_id,
                    text=t("attended_notify", v_lang, project=escape(project.title), balance=volunteer.balance),
                )
            except Exception:
                pass
            try:
                await ask_feedback(message.bot, volunteer.tg_id, project.id, project.title)
            except Exception:
                pass
        return

    # --- STANDARD GREETING FLOW ---
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()

    # «Пригласи друга»: пришёл по ссылке ?start=ref_<tg> и его ещё нет в базе — запоминаем, кто пригласил
    if args and args.startswith('ref_') and not user:
        try:
            from app_telegram import referrals
            await sync_to_async(referrals.remember)(message.from_user.id, int(args[4:]))
        except ValueError:
            pass

    if user:
        await message.answer(
            t("welcome_back", name=escape(user.fullname or message.from_user.full_name)),
            reply_markup=reply.hi_there(user.is_admin),
        )
    elif lang is None:
        # Новый человек — сначала язык, потом всё остальное уже на нём.
        await ask_language(message)
    else:
        await ask_if_registered(message)


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
