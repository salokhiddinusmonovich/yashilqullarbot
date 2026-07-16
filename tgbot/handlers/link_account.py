"""
ФАЙЛ — tgbot/handlers/link_account.py

Логика:
1. При /start, если юзера ещё нет в базе (см. обновлённый start.py)
   — вызывается ask_if_registered() ИЗ ЭТОГО ФАЙЛА вместо прямого
   показа старой кнопки auth_btn().
2. Если "Нет, впервые" — показываем ТУ ЖЕ auth_btn()-кнопку, что и
   раньше показывал start.py. Дальше всё идёт как шло: нажатие на неё
   само запускает твою обычную регистрацию в register.py — этот файл
   тут больше ничего не трогает.
3. Если "Да, уже регистрировался" — спрашиваем email, потом пароль,
   ищем TGUser по email, проверяем пароль через user.check_password()
   (метод уже есть в модели), и если верно — привязываем tg_id этого
   чата к найденному юзеру.
4. После привязки — проверяем, чего не хватает (телефон, bio), и
   спрашиваем только недостающее.
5. В конце — сообщение, что доступ к Mini App открыт.
"""
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async


class LinkAccountStates(StatesGroup):
    waiting_for_choice = State()
    waiting_for_email = State()
    waiting_for_password = State()
    waiting_for_phone = State()
    waiting_for_bio = State()


def already_registered_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Ha, saytda ro'yxatdan o'tganman", callback_data="acc_has_website"),
        InlineKeyboardButton("🆕 Yo'q, birinchi marta", callback_data="acc_new_user"),
    )
    return kb


async def ask_if_registered(message: types.Message):
    """
    ВЫЗЫВАТЬ ЭТО вместо прямого запуска регистрации на /start.
    """
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "Bizning saytimizda (yashilqollar.uz) email va parol bilan "
        "allaqachon ro'yxatdan o'tganmisiz?",
        reply_markup=already_registered_keyboard(),
    )
    await LinkAccountStates.waiting_for_choice.set()


async def process_choice(call: types.CallbackQuery, state: FSMContext):
    if call.data == "acc_new_user":
        await state.finish()
        from aiogram.utils.markdown import hbold
        from ..keyboards import reply
        await call.message.answer(
            f"👋 Salom, {hbold(call.from_user.full_name)}! @YashilQollar oilasiga xush kelibsiz.",
            reply_markup=reply.auth_btn(),
            parse_mode="HTML",
        )
        await call.answer()
        return

    # acc_has_website
    await call.message.edit_text("Saytda ro'yxatdan o'tgan email manzilingizni yozing 👇")
    await LinkAccountStates.waiting_for_email.set()
    await call.answer()


async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip().lower()
    await state.update_data(email=email)
    await message.answer("Endi parolingizni yozing 👇")
    await LinkAccountStates.waiting_for_password.set()


@sync_to_async
def find_and_link_user(email: str, password: str, tg_id: int, tg_username: str | None):
    """
    Возвращает (user, error_text). Если ошибка — user is None.
    """
    from app_telegram.models import TGUser

    try:
        user = TGUser.objects.get(email=email)
    except TGUser.DoesNotExist:
        return None, "❌ Bunday email bilan hisob topilmadi. Email manzilni tekshirib, qayta urinib ko'ring."

    if not user.password:
        return None, "❌ Bu hisob parolsiz (Telegram orqali ro'yxatdan o'tgan). Iltimos, \"Yo'q, birinchi marta\" tugmasini bosing."

    if not user.check_password(password):
        return None, "❌ Parol noto'g'ri. Qayta urinib ko'ring."

    if user.tg_id and user.tg_id != tg_id:
        return None, "⚠️ Bu hisob allaqachon boshqa Telegram akkauntga bog'langan. Agar bu xato bo'lsa, admin bilan bog'laning."

    user.tg_id = tg_id
    if tg_username:
        user.username = tg_username
    user.save(update_fields=['tg_id', 'username'])
    return user, None


async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    email = data.get('email')
    tg_id = message.from_user.id
    tg_username = message.from_user.username

    user, error = await find_and_link_user(email, message.text, tg_id, tg_username)

    if error:
        await message.answer(error + "\n\nEmailni qayta yozing 👇")
        await LinkAccountStates.waiting_for_email.set()
        return

    await message.answer(f"✅ Xush kelibsiz, {user.fullname}! Hisobingiz Telegram bilan bog'landi.")

    # Дозаполняем недостающее
    if not user.phone:
        await state.update_data(user_id=user.id)
        await message.answer(
            "Telefon raqamingizni yuboring 👇",
            reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                types.KeyboardButton("📱 Raqamni yuborish", request_contact=True)
            ),
        )
        await LinkAccountStates.waiting_for_phone.set()
        return

    await finish_link_flow(message, state, user.id)


async def process_phone(message: types.Message, state: FSMContext):
    if not message.contact:
        await message.answer("Iltimos, tugma orqali telefon raqam yuboring 👇")
        return

    data = await state.get_data()
    user_id = data.get('user_id')

    @sync_to_async
    def save_phone():
        from app_telegram.models import TGUser
        user = TGUser.objects.get(id=user_id)
        user.phone = message.contact.phone_number
        user.save(update_fields=['phone'])
        return user

    user = await save_phone()

    if not user.bio:
        await message.answer(
            "Va oxirgi savol — o'zingiz haqingizda bir necha so'z yozing "
            "(qiziqishlar, tajriba va h.k.) 👇",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        await LinkAccountStates.waiting_for_bio.set()
        return

    await finish_link_flow(message, state, user_id)


async def process_bio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('user_id')

    @sync_to_async
    def save_bio():
        from app_telegram.models import TGUser
        user = TGUser.objects.get(id=user_id)
        user.bio = message.text
        user.save(update_fields=['bio'])

    await save_bio()
    await finish_link_flow(message, state, user_id)


async def finish_link_flow(message: types.Message, state: FSMContext, user_id: int):
    await state.finish()
    bot_info = await message.bot.get_me()
    await message.answer(
        "🎉 Profilingiz to'liq! Endi Mini App'ga kirishingiz mumkin — "
        "pastdagi menyu tugmasini bosing.",
    )


def register_link_account_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        process_choice, lambda c: c.data in ("acc_has_website", "acc_new_user"),
        state=LinkAccountStates.waiting_for_choice,
    )
    dp.register_message_handler(process_email, state=LinkAccountStates.waiting_for_email)
    dp.register_message_handler(process_password, state=LinkAccountStates.waiting_for_password)
    dp.register_message_handler(
        process_phone, content_types=types.ContentType.CONTACT,
        state=LinkAccountStates.waiting_for_phone,
    )
    dp.register_message_handler(process_bio, state=LinkAccountStates.waiting_for_bio)