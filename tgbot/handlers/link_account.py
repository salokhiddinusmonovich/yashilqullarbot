"""
ФАЙЛ — tgbot/handlers/link_account.py

Привязка аккаунта с сайта (yashilqollar.uz) к Telegram.

Сюда попадают двумя путями:
1. /start → "Ha, saytda ro'yxatdan o'tganman" → вводит email.
2. Обычная регистрация в боте (register.py): на шаге email бот видит,
   что такой email уже есть на сайте, и сам предлагает привязку
   через offer_link() — вместо старого тупика "email allaqachon band".

Подтвердить, что аккаунт твой, можно тремя способами:
  🔑 паролем с сайта (если он есть),
  📧 6-значным кодом на почту (если забыл пароль или входил через Google),
  🙋 через админа — запасной вариант, если почта не настроена/не дошла.

После привязки спрашиваем только то, чего не хватает (телефон, регион),
и показываем главное меню + короткую инструкцию.
"""
import logging
import secrets
import time

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from html import escape

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import IntegrityError

from tgbot.i18n import t, region_from_text
from tgbot.services.lang import langs_of, lang_of
from ..keyboards import reply
from ..keyboards.reply import region_kb
from .help import send_guide

logger = logging.getLogger(__name__)

CODE_TTL = 10 * 60        # код живёт 10 минут
CODE_RESEND_AFTER = 60    # повторно отправить можно через минуту
CODE_MAX_ATTEMPTS = 5


class LinkAccountStates(StatesGroup):
    waiting_for_choice = State()
    waiting_for_email = State()
    waiting_for_method = State()
    waiting_for_password = State()
    waiting_for_code = State()
    waiting_for_phone = State()
    waiting_for_region = State()


def already_registered_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(t("btn_has_site"), callback_data="acc_has_website"),
        InlineKeyboardButton(t("btn_first_time"), callback_data="acc_new_user"),
    )
    return kb


def email_enabled() -> bool:
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def method_keyboard(has_password: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    if has_password:
        kb.add(InlineKeyboardButton(t("btn_login_password"), callback_data="link_pw"))
    if email_enabled():
        kb.add(InlineKeyboardButton(t("btn_email_code"), callback_data="link_code"))
    else:
        kb.add(InlineKeyboardButton(t("btn_admin_confirm"), callback_data="link_admin"))
    kb.add(InlineKeyboardButton(t("btn_other_email"), callback_data="link_other"))
    return kb


# ─────────────────────────── вход в поток ───────────────────────────

async def ask_if_registered(message: types.Message):
    """Вызывается из /start, если юзера с таким tg_id ещё нет в базе."""
    await message.answer(t("ask_has_site_account"), reply_markup=already_registered_keyboard())
    await LinkAccountStates.waiting_for_choice.set()


async def process_choice(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if call.data == "acc_new_user":
        await state.finish()
        await call.message.answer(
            t("new_user_welcome", name=escape(call.from_user.full_name)),
            reply_markup=reply.auth_btn(),
        )
        return

    # acc_has_website
    await call.message.answer(t("ask_site_email"))
    await LinkAccountStates.waiting_for_email.set()


@sync_to_async
def _find_by_email(email: str):
    from app_telegram.models import TGUser
    return TGUser.objects.filter(email__iexact=email).first()


async def process_email(message: types.Message, state: FSMContext):
    email = (message.text or "").strip()
    user = await _find_by_email(email)

    if not user:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(t("btn_new_signup"), callback_data="acc_new_user")
        )
        await message.answer(t("email_not_found"), reply_markup=kb)
        return

    await offer_link(message, state, user)


async def offer_link(message: types.Message, state: FSMContext, user):
    """
    Показывает найденный аккаунт и способы подтверждения.
    Вызывается и из этого файла, и из register.py (шаг email).
    """
    tg_id = message.from_user.id

    if user.tg_id == tg_id:
        await state.finish()
        await message.answer(t("already_linked_self"), reply_markup=reply.hi_there(user.is_admin))
        return

    if user.tg_id:
        await state.finish()
        await message.answer(t("linked_other_tg"), reply_markup=reply.auth_btn())
        return

    await state.set_state(LinkAccountStates.waiting_for_method.state)
    await state.update_data(link_user_id=user.id, link_email=user.email)
    await message.answer(
        t("account_found", name=escape(user.fullname or "—"), email=escape(user.email)),
        reply_markup=method_keyboard(bool(user.password)),
    )


async def process_method(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    if not data.get("link_user_id"):
        await call.message.answer(t("session_expired"))
        await state.finish()
        return

    if call.data == "link_pw":
        await LinkAccountStates.waiting_for_password.set()
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(t("btn_forgot_password"), callback_data="link_code")
        ) if email_enabled() else None
        await call.message.answer(t("ask_password"), reply_markup=kb)

    elif call.data == "link_code":
        await _send_code(call.message, state, call.from_user.id)

    elif call.data == "link_admin":
        await _ask_admins(call.message.bot, call.from_user, data)
        await state.finish()
        await call.message.answer(t("admin_request_sent"))

    elif call.data == "link_other":
        await LinkAccountStates.waiting_for_email.set()
        await call.message.answer(t("ask_email_again"))


# ─────────────────────────── пароль ───────────────────────────

async def process_password(message: types.Message, state: FSMContext):
    from app_telegram.models import TGUser
    data = await state.get_data()
    user = await sync_to_async(TGUser.objects.filter(id=data.get("link_user_id")).first)()
    if not user:
        await state.finish()
        await message.answer(t("session_expired"))
        return

    try:
        await message.delete()  # не оставляем пароль в чате
    except Exception:
        pass

    if not user.check_password(message.text or ""):
        await message.answer(t("wrong_password"), reply_markup=method_keyboard(bool(user.password)))
        return

    await _link_and_continue(message, state, data["link_user_id"])


# ─────────────────────────── код на почту ───────────────────────────

@sync_to_async
def _mail_code(email: str, code: str):
    from django.core.mail import send_mail
    send_mail(
        subject=t("code_email_subject"),
        message=t("code_email_body", code=code),
        from_email=None,
        recipient_list=[email],
    )


async def _send_code(message: types.Message, state: FSMContext, tg_id: int):
    data = await state.get_data()
    sent_at = data.get("code_sent_at", 0)
    if time.time() - sent_at < CODE_RESEND_AFTER:
        wait = int(CODE_RESEND_AFTER - (time.time() - sent_at))
        await message.answer(t("code_wait", sec=wait))
        return

    code = f"{secrets.randbelow(1_000_000):06d}"
    email = data["link_email"]
    try:
        await _mail_code(email, code)
    except Exception as e:
        logger.error("Failed to send link code to %s: %s", email, e)
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(t("btn_admin_confirm"), callback_data="link_admin")
        )
        await message.answer(t("email_send_failed"), reply_markup=kb)
        return

    await state.update_data(code=code, code_sent_at=time.time(), code_attempts=0)
    await LinkAccountStates.waiting_for_code.set()

    kb = InlineKeyboardMarkup().add(InlineKeyboardButton(t("btn_resend"), callback_data="link_code"))
    await message.answer(t("code_sent", email=escape(_mask_email(email))), reply_markup=kb)


def _mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    visible = name[:2] if len(name) > 2 else name[:1]
    return f"{visible}{'*' * max(len(name) - len(visible), 1)}@{domain}"


async def process_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    entered = "".join(ch for ch in (message.text or "") if ch.isdigit())

    if not data.get("code") or time.time() - data.get("code_sent_at", 0) > CODE_TTL:
        await message.answer(t("code_expired"))
        return

    if entered != data["code"]:
        attempts = data.get("code_attempts", 0) + 1
        if attempts >= CODE_MAX_ATTEMPTS:
            await state.update_data(code=None)
            await message.answer(t("code_too_many"))
            return
        await state.update_data(code_attempts=attempts)
        await message.answer(t("code_wrong", left=CODE_MAX_ATTEMPTS - attempts))
        return

    await _link_and_continue(message, state, data["link_user_id"])


async def process_code_resend(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await _send_code(call.message, state, call.from_user.id)


# ─────────────────────────── через админа ───────────────────────────

@sync_to_async
def _admin_ids(bot) -> set:
    from app_telegram.models import TGUser
    ids = set(TGUser.objects.filter(is_admin=True, tg_id__isnull=False).values_list("tg_id", flat=True))
    ids.update(bot["config"].tg_bot.admin_ids)
    return ids


async def _ask_admins(bot, tg_user: types.User, data: dict):
    admin_ids = await _admin_ids(bot)
    langs = await langs_of(admin_ids)
    for admin_id in admin_ids:
        lang = langs.get(admin_id)
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(t("btn_link_yes", lang), callback_data=f"admlink:{data['link_user_id']}:{tg_user.id}"),
            InlineKeyboardButton(t("btn_link_no", lang), callback_data=f"admlink_no:{tg_user.id}"),
        )
        text = t(
            "adm_link_request", lang,
            tg=escape(tg_user.full_name),
            uname=f"@{tg_user.username}" if tg_user.username else t("no_username", lang),
            tg_id=tg_user.id,
            email=escape(data.get("link_email") or ""),
        )
        try:
            await bot.send_message(admin_id, text, reply_markup=kb)
        except Exception:
            pass


async def admin_link_decision(call: types.CallbackQuery):
    from app_telegram.models import TGUser
    admin = await sync_to_async(TGUser.objects.filter(tg_id=call.from_user.id, is_admin=True).first)()
    if not admin and call.from_user.id not in call.bot["config"].tg_bot.admin_ids:
        await call.answer(t("no_access"), show_alert=True)
        return

    if call.data.startswith("admlink_no:"):
        tg_id = int(call.data.split(":")[1])
        await call.message.edit_text(call.message.html_text + "\n\n" + t("adm_link_declined_mark"))
        try:
            await call.bot.send_message(tg_id, t("link_declined_user", await lang_of(tg_id)))
        except Exception:
            pass
        await call.answer()
        return

    _, user_id, tg_id = call.data.split(":")
    user, error = await _link_user(int(user_id), int(tg_id), None)
    if error:
        await call.answer(t(error), show_alert=True)
        return
    await call.message.edit_text(
        call.message.html_text + "\n\n" + t("adm_link_done_mark", admin=escape(call.from_user.full_name))
    )
    await call.answer(t("linked_short"))
    try:
        await call.bot.send_message(int(tg_id), t("link_approved_user", await lang_of(int(tg_id)), email=escape(user.email)))
    except Exception:
        pass


# ─────────────────────────── привязка + дозаполнение ───────────────────────────

@sync_to_async
def _link_user(user_id: int, tg_id: int, tg_username):
    """Возвращает (user, error_key) — error_key это ключ перевода для t()."""
    from app_telegram.models import TGUser

    user = TGUser.objects.filter(id=user_id).first()
    if not user:
        return None, "err_account_not_found"
    if user.tg_id and user.tg_id != tg_id:
        return None, "err_account_other_tg"
    if TGUser.objects.filter(tg_id=tg_id).exclude(id=user_id).exists():
        return None, "err_tg_other_account"

    user.tg_id = tg_id
    if tg_username:
        user.username = tg_username
    try:
        user.save(update_fields=["tg_id", "username"])
    except IntegrityError:
        return None, "err_tg_other_account"
    return user, None


async def _link_and_continue(message: types.Message, state: FSMContext, user_id: int):
    user, error = await _link_user(user_id, message.from_user.id, message.from_user.username)
    if error:
        await state.finish()
        await message.answer(t(error))
        return

    await state.update_data(link_user_id=user.id, code=None)
    await message.answer(t("link_success", name=escape(user.fullname or "")))
    await _ask_missing(message, state, user)


async def _ask_missing(message: types.Message, state: FSMContext, user):
    from app_telegram.models import TGUser

    if not user.phone:
        await LinkAccountStates.waiting_for_phone.set()
        await message.answer(t("ask_phone"), reply_markup=reply.contact_btn())
        return

    if user.region not in TGUser.Region.values:
        await LinkAccountStates.waiting_for_region.set()
        await message.answer(t("ask_region"), reply_markup=region_kb())
        return

    await state.finish()
    await message.answer(t("profile_ready"), reply_markup=reply.hi_there(user.is_admin))
    await send_guide(message)


async def process_phone(message: types.Message, state: FSMContext):
    from app_telegram.models import TGUser
    if not message.contact:
        await message.answer(t("phone_use_button"), reply_markup=reply.contact_btn())
        return

    data = await state.get_data()
    user = await sync_to_async(TGUser.objects.get)(id=data["link_user_id"])
    user.phone = message.contact.phone_number
    await sync_to_async(user.save)(update_fields=["phone"])
    await _ask_missing(message, state, user)


async def process_region(message: types.Message, state: FSMContext):
    from app_telegram.models import TGUser
    region = region_from_text(message.text)
    if not region:
        await message.answer(t("use_buttons"), reply_markup=region_kb())
        return

    data = await state.get_data()
    user = await sync_to_async(TGUser.objects.get)(id=data["link_user_id"])
    user.region = region
    await sync_to_async(user.save)(update_fields=["region"])
    await _ask_missing(message, state, user)


def register_link_account_handlers(dp: Dispatcher):
    # state="*" — чтобы кнопки из старых сообщений тоже срабатывали
    dp.register_callback_query_handler(
        process_choice, lambda c: c.data in ("acc_has_website", "acc_new_user"), state="*",
    )
    dp.register_callback_query_handler(
        process_code_resend, lambda c: c.data == "link_code", state=LinkAccountStates.waiting_for_code,
    )
    dp.register_callback_query_handler(
        process_method, lambda c: c.data in ("link_pw", "link_code", "link_admin", "link_other"),
        state=[LinkAccountStates.waiting_for_method, LinkAccountStates.waiting_for_password,
               LinkAccountStates.waiting_for_code],
    )
    dp.register_callback_query_handler(
        admin_link_decision, lambda c: c.data.startswith(("admlink:", "admlink_no:")), state="*",
    )
    dp.register_message_handler(process_email, state=LinkAccountStates.waiting_for_email)
    dp.register_message_handler(process_password, state=LinkAccountStates.waiting_for_password)
    dp.register_message_handler(process_code, state=LinkAccountStates.waiting_for_code)
    dp.register_message_handler(
        process_phone, content_types=types.ContentType.CONTACT,
        state=LinkAccountStates.waiting_for_phone,
    )
    dp.register_message_handler(process_phone, state=LinkAccountStates.waiting_for_phone)  # текст вместо кнопки
    dp.register_message_handler(process_region, state=LinkAccountStates.waiting_for_region)
