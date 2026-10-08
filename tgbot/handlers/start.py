from html import escape

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from asgiref.sync import sync_to_async

from tgbot.i18n import t
from tgbot.services.lang import lang_of
from ..keyboards import reply
from ..keyboards.subscription import subscription_keyboard
from .qr_handler import process_qr_logic
from .feedback import ask_feedback
from .link_account import ask_if_registered
from .language import ask_language


CHANNEL_USERNAME = "@yashilqollar"


async def is_subscribed(bot, user_id: int) -> bool:
    """
    Проверяет, подписан ли пользователь на канал.
    """

    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        return member.status in (
            "creator",
            "administrator",
            "member"
        )

    except Exception:
        return False


async def user_start(
    message: Message,
    state: FSMContext,
    lang: str = None,
    _skip_subscription: bool = False,
    _args: str = None
):
    from app_telegram.models import TGUser, LoginToken

    # Получаем аргументы /start
    if _args is not None:
        args = _args
    else:
        args = message.get_args()

    # ---------------------------------------------------------
    # ПРОВЕРКА ПОДПИСКИ
    # ---------------------------------------------------------

    if not _skip_subscription:

        subscribed = await is_subscribed(
            message.bot,
            message.from_user.id
        )

        if not subscribed:

            # Сохраняем аргументы deep-link:
            # login_xxx
            # qr_xxx
            # ref_xxx
            await state.update_data(
                start_args=args or ""
            )

            await message.answer(
                "👋 Чтобы пользоваться ботом, сначала подпишитесь "
                "на наш официальный канал.\n\n"
                "После подписки нажмите кнопку "
                "«✅ Я подписался».",
                reply_markup=subscription_keyboard()
            )

            return

    # ---------------------------------------------------------
    # ДАЛЬШЕ ИДЁТ ТВОЯ СТАРАЯ ЛОГИКА
    # ---------------------------------------------------------

    await state.finish()

    # ---------------------------------------------------------
    # LOGIN VIA WEBSITE (deep-link)
    # ---------------------------------------------------------

    if args and args.startswith("login_"):

        token = args.replace("login_", "")

        tg_id = message.from_user.id
        fullname = message.from_user.full_name

        user, created = await sync_to_async(
            TGUser.objects.get_or_create
        )(
            tg_id=tg_id,
            defaults={
                "fullname": fullname,
                "username": message.from_user.username or "",
                "email": None,
                "phone": "",
            }
        )

        if not created:

            user.fullname = fullname

            if message.from_user.username:
                user.username = message.from_user.username

            await sync_to_async(user.save)(
                update_fields=[
                    "fullname",
                    "username"
                ]
            )

        updated = await sync_to_async(
            LoginToken.objects
            .filter(
                token=token,
                status="pending"
            )
            .update
        )(
            status="confirmed",
            tg_id=tg_id
        )

        await message.answer(
            t("login_confirmed")
            if updated
            else t("login_expired")
        )

        return

    # ---------------------------------------------------------
    # QR CODE SCANNING VIA DEEP LINK
    # ---------------------------------------------------------

    if args and args.startswith("qr_"):

        try:
            target_id = int(
                args.replace("qr_", "")
            )

        except ValueError:

            await message.answer(
                t("qr_bad_format")
            )

            return

        # Админ — любой регион и прошедшие мероприятия
        scanner = await sync_to_async(
            TGUser.objects
            .filter(
                tg_id=message.from_user.id,
                is_admin=True
            )
            .first
        )()

        if scanner:

            from .admin_scan import admin_pick

            await admin_pick(
                message,
                target_id
            )

            return

        result_text, volunteer, project, confirmed = (
            await process_qr_logic(
                message.from_user.id,
                target_id
            )
        )

        await message.answer(result_text)

        if confirmed:

            # Уведомление — на языке волонтёра
            v_lang = await lang_of(
                volunteer.tg_id
            )

            try:

                await message.bot.send_message(
                    chat_id=volunteer.tg_id,
                    text=t(
                        "attended_notify",
                        v_lang,
                        project=escape(
                            project.title
                        ),
                        balance=volunteer.balance
                    ),
                )

            except Exception:
                pass

            try:

                await ask_feedback(
                    message.bot,
                    volunteer.tg_id,
                    project.id,
                    project.title
                )

            except Exception:
                pass

        return

    # ---------------------------------------------------------
    # STANDARD GREETING FLOW
    # ---------------------------------------------------------

    user = await sync_to_async(
        TGUser.objects
        .filter(
            tg_id=message.from_user.id
        )
        .first
    )()

    # «Пригласи друга»
    if (
        args
        and args.startswith("ref_")
        and not user
    ):

        try:

            from app_telegram import referrals

            await sync_to_async(
                referrals.remember
            )(
                message.from_user.id,
                int(args[4:])
            )

        except ValueError:
            pass

    if user:

        await message.answer(
            t(
                "welcome_back",
                name=escape(
                    user.fullname
                    or message.from_user.full_name
                )
            ),
            reply_markup=reply.hi_there(
                user.is_admin
            ),
        )

    elif lang is None:

        # Новый человек — сначала язык
        await ask_language(message)

    else:

        await ask_if_registered(message)


def register_user(dp: Dispatcher):

    dp.register_message_handler(
        user_start,
        commands=["start"],
        state="*"
    )