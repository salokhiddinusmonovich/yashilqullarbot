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
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import IntegrityError

from ..keyboards import reply
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
        InlineKeyboardButton("✅ Ha, saytda ro'yxatdan o'tganman", callback_data="acc_has_website"),
        InlineKeyboardButton("🆕 Yo'q, birinchi marta", callback_data="acc_new_user"),
    )
    return kb


def email_enabled() -> bool:
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def method_keyboard(has_password: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    if has_password:
        kb.add(InlineKeyboardButton("🔑 Parol bilan kirish", callback_data="link_pw"))
    if email_enabled():
        kb.add(InlineKeyboardButton("📧 Emailga kod yuborish (parolni unutdim)", callback_data="link_code"))
    else:
        kb.add(InlineKeyboardButton("🙋 Admin orqali tasdiqlash", callback_data="link_admin"))
    kb.add(InlineKeyboardButton("✏️ Boshqa email kiritish", callback_data="link_other"))
    return kb


def region_keyboard() -> ReplyKeyboardMarkup:
    from app_telegram.models import TGUser
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for _, label in TGUser.Region.choices:
        kb.add(KeyboardButton(label))
    return kb


# ─────────────────────────── вход в поток ───────────────────────────

async def ask_if_registered(message: types.Message):
    """Вызывается из /start, если юзера с таким tg_id ещё нет в базе."""
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "Bizning saytimizda (yashilqollar.uz) allaqachon ro'yxatdan o'tganmisiz?",
        reply_markup=already_registered_keyboard(),
    )
    await LinkAccountStates.waiting_for_choice.set()


async def process_choice(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if call.data == "acc_new_user":
        await state.finish()
        from aiogram.utils.markdown import hbold
        await call.message.answer(
            f"👋 Salom, {hbold(call.from_user.full_name)}! @YashilQollar oilasiga xush kelibsiz.\n\n"
            "Ro'yxatdan o'tish uchun pastdagi tugmani bosing 👇",
            reply_markup=reply.auth_btn(),
            parse_mode="HTML",
        )
        return

    # acc_has_website
    await call.message.answer("Saytda ro'yxatdan o'tgan email manzilingizni yozing 👇")
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
            InlineKeyboardButton("🆕 Yangi ro'yxatdan o'tish", callback_data="acc_new_user")
        )
        await message.answer(
            "❌ Bunday email bilan hisob topilmadi.\n\n"
            "Emailni tekshirib qayta yozing yoki yangi ro'yxatdan o'ting 👇",
            reply_markup=kb,
        )
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
        await message.answer("✅ Bu hisob allaqachon sizning Telegramingizga bog'langan.",
                             reply_markup=reply.hi_there(user.is_admin))
        return

    if user.tg_id:
        await state.finish()
        await message.answer(
            "⚠️ Bu email boshqa Telegram akkauntga bog'langan.\n"
            "Agar bu sizning hisobingiz bo'lsa, admin bilan bog'laning.",
            reply_markup=reply.auth_btn(),
        )
        return

    await state.set_state(LinkAccountStates.waiting_for_method.state)
    await state.update_data(link_user_id=user.id, link_email=user.email)
    await message.answer(
        f"🔎 Saytda hisob topildi: <b>{user.fullname}</b> ({user.email})\n\n"
        "Qayta ro'yxatdan o'tish shart emas — shu hisobni Telegramga bog'laymiz. "
        "Bu sizning hisobingiz ekanini tasdiqlang 👇",
        reply_markup=method_keyboard(bool(user.password)),
        parse_mode="HTML",
    )


async def process_method(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    if not data.get("link_user_id"):
        await call.message.answer("Sessiya tugadi. /start ni bosing.")
        await state.finish()
        return

    if call.data == "link_pw":
        await LinkAccountStates.waiting_for_password.set()
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("📧 Parolni unutdim — emailga kod", callback_data="link_code")
        ) if email_enabled() else None
        await call.message.answer("Saytdagi parolingizni yozing 👇", reply_markup=kb)

    elif call.data == "link_code":
        await _send_code(call.message, state, call.from_user.id)

    elif call.data == "link_admin":
        await _ask_admins(call.message.bot, call.from_user, data)
        await state.finish()
        await call.message.answer(
            "🙋 So'rovingiz adminlarga yuborildi. Tasdiqlashlari bilan sizga xabar keladi."
        )

    elif call.data == "link_other":
        await LinkAccountStates.waiting_for_email.set()
        await call.message.answer("Email manzilingizni yozing 👇")


# ─────────────────────────── пароль ───────────────────────────

async def process_password(message: types.Message, state: FSMContext):
    from app_telegram.models import TGUser
    data = await state.get_data()
    user = await sync_to_async(TGUser.objects.filter(id=data.get("link_user_id")).first)()
    if not user:
        await state.finish()
        await message.answer("Xatolik. /start ni bosing.")
        return

    try:
        await message.delete()  # не оставляем пароль в чате
    except Exception:
        pass

    if not user.check_password(message.text or ""):
        await message.answer(
            "❌ Parol noto'g'ri. Qayta yozing yoki boshqa usulni tanlang 👇",
            reply_markup=method_keyboard(bool(user.password)),
        )
        return

    await _link_and_continue(message, state, data["link_user_id"])


# ─────────────────────────── код на почту ───────────────────────────

@sync_to_async
def _mail_code(email: str, code: str):
    from django.core.mail import send_mail
    send_mail(
        subject="Yashil Qo'llar — tasdiqlash kodi",
        message=(
            f"Sizning tasdiqlash kodingiz: {code}\n\n"
            "Kodni @YashilQollar botiga yuboring. Kod 10 daqiqa amal qiladi.\n"
            "Agar siz so'ramagan bo'lsangiz — bu xatni e'tiborsiz qoldiring."
        ),
        from_email=None,
        recipient_list=[email],
    )


async def _send_code(message: types.Message, state: FSMContext, tg_id: int):
    data = await state.get_data()
    sent_at = data.get("code_sent_at", 0)
    if time.time() - sent_at < CODE_RESEND_AFTER:
        wait = int(CODE_RESEND_AFTER - (time.time() - sent_at))
        await message.answer(f"⏳ Kod yaqinda yuborildi. Qayta yuborish uchun {wait} soniya kuting.")
        return

    code = f"{secrets.randbelow(1_000_000):06d}"
    email = data["link_email"]
    try:
        await _mail_code(email, code)
    except Exception as e:
        logger.error("Failed to send link code to %s: %s", email, e)
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("🙋 Admin orqali tasdiqlash", callback_data="link_admin")
        )
        await message.answer("⚠️ Emailga xat yuborib bo'lmadi. Admin orqali tasdiqlashingiz mumkin 👇",
                             reply_markup=kb)
        return

    await state.update_data(code=code, code_sent_at=time.time(), code_attempts=0)
    await LinkAccountStates.waiting_for_code.set()

    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🔁 Qayta yuborish", callback_data="link_code"))
    await message.answer(
        f"📧 <b>{_mask_email(email)}</b> manziliga 6 xonali kod yubordik.\n"
        "Kodni shu yerga yozing 👇\n\n"
        "<i>Xat kelmasa — «Spam» papkasini tekshiring.</i>",
        reply_markup=kb,
        parse_mode="HTML",
    )


def _mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    visible = name[:2] if len(name) > 2 else name[:1]
    return f"{visible}{'*' * max(len(name) - len(visible), 1)}@{domain}"


async def process_code(message: types.Message, state: FSMContext):
    data = await state.get_data()
    entered = "".join(ch for ch in (message.text or "") if ch.isdigit())

    if not data.get("code") or time.time() - data.get("code_sent_at", 0) > CODE_TTL:
        await message.answer("⌛ Kod eskirgan. «🔁 Qayta yuborish» tugmasini bosing.")
        return

    if entered != data["code"]:
        attempts = data.get("code_attempts", 0) + 1
        if attempts >= CODE_MAX_ATTEMPTS:
            await state.update_data(code=None)
            await message.answer("❌ Juda ko'p noto'g'ri urinish. «🔁 Qayta yuborish» bilan yangi kod oling.")
            return
        await state.update_data(code_attempts=attempts)
        await message.answer(f"❌ Kod noto'g'ri. Qolgan urinishlar: {CODE_MAX_ATTEMPTS - attempts}")
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
    uname = f"@{tg_user.username}" if tg_user.username else "username yo'q"
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Bog'lash", callback_data=f"admlink:{data['link_user_id']}:{tg_user.id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"admlink_no:{tg_user.id}"),
    )
    text = (
        "🙋 <b>Hisobni bog'lash so'rovi</b>\n\n"
        f"Telegram: {tg_user.full_name} ({uname}, <code>{tg_user.id}</code>)\n"
        f"Saytdagi hisob: <b>{data.get('link_email')}</b>\n\n"
        "Bu shu odamning hisobi ekaniga ishonchingiz komilmi?"
    )
    for admin_id in await _admin_ids(bot):
        try:
            await bot.send_message(admin_id, text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


async def admin_link_decision(call: types.CallbackQuery):
    from app_telegram.models import TGUser
    admin = await sync_to_async(TGUser.objects.filter(tg_id=call.from_user.id, is_admin=True).first)()
    if not admin and call.from_user.id not in call.bot["config"].tg_bot.admin_ids:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return

    if call.data.startswith("admlink_no:"):
        tg_id = int(call.data.split(":")[1])
        await call.message.edit_text(call.message.html_text + "\n\n❌ <b>Rad etildi</b>", parse_mode="HTML")
        try:
            await call.bot.send_message(tg_id, "❌ Hisobni bog'lash so'rovi rad etildi. Admin bilan bog'laning.")
        except Exception:
            pass
        await call.answer()
        return

    _, user_id, tg_id = call.data.split(":")
    user, error = await _link_user(int(user_id), int(tg_id), None)
    if error:
        await call.answer(error, show_alert=True)
        return
    await call.message.edit_text(
        call.message.html_text + f"\n\n✅ <b>Bog'landi</b> ({call.from_user.full_name})", parse_mode="HTML"
    )
    await call.answer("Bog'landi")
    try:
        await call.bot.send_message(
            int(tg_id),
            f"✅ Admin tasdiqladi! Hisobingiz ({user.email}) Telegramga bog'landi.\n"
            "Davom etish uchun /start ni bosing.",
        )
    except Exception:
        pass


# ─────────────────────────── привязка + дозаполнение ───────────────────────────

@sync_to_async
def _link_user(user_id: int, tg_id: int, tg_username):
    """Возвращает (user, error_text)."""
    from app_telegram.models import TGUser

    user = TGUser.objects.filter(id=user_id).first()
    if not user:
        return None, "❌ Hisob topilmadi."
    if user.tg_id and user.tg_id != tg_id:
        return None, "⚠️ Bu hisob allaqachon boshqa Telegram akkauntga bog'langan."
    if TGUser.objects.filter(tg_id=tg_id).exclude(id=user_id).exists():
        return None, "⚠️ Bu Telegram akkaunt boshqa hisobga bog'langan. Admin bilan bog'laning."

    user.tg_id = tg_id
    if tg_username:
        user.username = tg_username
    try:
        user.save(update_fields=["tg_id", "username"])
    except IntegrityError:
        return None, "⚠️ Bu Telegram akkaunt boshqa hisobga bog'langan. Admin bilan bog'laning."
    return user, None


async def _link_and_continue(message: types.Message, state: FSMContext, user_id: int):
    user, error = await _link_user(user_id, message.from_user.id, message.from_user.username)
    if error:
        await state.finish()
        await message.answer(error)
        return

    await state.update_data(link_user_id=user.id, code=None)
    await message.answer(f"✅ Xush kelibsiz, {user.fullname}! Hisobingiz Telegram bilan bog'landi.")
    await _ask_missing(message, state, user)


async def _ask_missing(message: types.Message, state: FSMContext, user):
    from app_telegram.models import TGUser

    if not user.phone:
        await LinkAccountStates.waiting_for_phone.set()
        await message.answer("📱 Telefon raqamingizni yuboring 👇", reply_markup=reply.contact_btn())
        return

    if user.region not in TGUser.Region.values:
        await LinkAccountStates.waiting_for_region.set()
        await message.answer(
            "📍 Qaysi hududdansiz? Tadbirlar hudud bo'yicha ko'rsatiladi 👇",
            reply_markup=region_keyboard(),
        )
        return

    await state.finish()
    await message.answer("🎉 Profilingiz tayyor!", reply_markup=reply.hi_there(user.is_admin))
    await send_guide(message)


async def process_phone(message: types.Message, state: FSMContext):
    from app_telegram.models import TGUser
    if not message.contact:
        await message.answer("Iltimos, tugma orqali telefon raqam yuboring 👇")
        return

    data = await state.get_data()
    user = await sync_to_async(TGUser.objects.get)(id=data["link_user_id"])
    user.phone = message.contact.phone_number
    await sync_to_async(user.save)(update_fields=["phone"])
    await _ask_missing(message, state, user)


async def process_region(message: types.Message, state: FSMContext):
    from app_telegram.models import TGUser
    region = next((v for v, label in TGUser.Region.choices if label == (message.text or "").strip()), None)
    if not region:
        await message.answer("Iltimos, pastdagi tugmalardan birini tanlang 👇", reply_markup=region_keyboard())
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
    dp.register_message_handler(process_region, state=LinkAccountStates.waiting_for_region)
