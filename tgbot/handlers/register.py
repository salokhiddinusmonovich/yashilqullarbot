from aiogram import Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from asgiref.sync import sync_to_async
import re

from django.db import IntegrityError
from ..keyboards.text import register_text
from ..keyboards.reply import contact_btn
from ..keyboards import reply
from app_telegram.models import TGUser
from django.core.files import File
from io import BytesIO
from django.core.files.base import ContentFile

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


# FSM States
class RegisterState(StatesGroup):
    fullname = State()
    age = State()
    email = State()
    region = State()
    education = State()
    experience = State()
    photo = State()
    phone = State()

# Step 1: Fullname
async def register_handler(message: Message, state: FSMContext):
    await state.set_state(RegisterState.fullname.state)
    await message.answer("Ism va familiyangizni kiriting")


async def fullname_handler(message: Message, state: FSMContext):
    await state.update_data(fullname=message.text.strip())
    await state.set_state(RegisterState.age.state)
    await message.answer("Yoshingizni kiriting 👇")


# Step 2: Age
async def age_handle(message: Message, state: FSMContext):
    age_str = message.text.strip()
    if not age_str.isdigit() or not (5 <= int(age_str) <= 120):
        await message.answer("Iltimos, yoshingizni 5 dan 120 gacha bo‘lgan raqam bilan kiriting.")
        return
    await state.update_data(age=int(age_str))
    await state.set_state(RegisterState.email.state)
    await message.answer("Email manzilingizni kiriting 👇")


# Step 3: Email
async def email_handler(message: Message, state: FSMContext):
    email = message.text.strip()
    if not EMAIL_REGEX.match(email):
        await message.answer("Iltimos, to‘g‘ri email kiriting (mas: user@gmail.com)")
        return

    await state.update_data(email=email)

    # Step 4: Region input as text
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for value, label in TGUser.Region.choices:
        kb.add(KeyboardButton(label))

    await state.set_state(RegisterState.region.state)
    await message.answer("Qaysi hududdansiz? (shahar yoki viloyat nomini kiriting)", reply_markup=kb)


# Step 4: Region text handler
async def region_handler(message: Message, state: FSMContext):
    selected_label = message.text.strip()

    # Ищем ключ (value) по тексту кнопки (label)
    region_value = None
    for value, label in TGUser.Region.choices:
        if selected_label == label:
            region_value = value
            break

    # ИСПРАВЛЕНО: если это не точное совпадение с кнопкой — просим выбрать
    # заново, вместо того чтобы сохранять произвольный введённый текст.
    # Именно из-за "final_region = region_value if region_value else
    # selected_label" в базе накопился разнобой вида "Toshkent shahri",
    # "Toshkent  shahri" (двойной пробел), "Tashkent shahar" и т.д. —
    # семь разных вариантов одного и того же региона, ни один не совпадал
    # с реальным кодом в TGUser.Region.choices.
    if not region_value:
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for value, label in TGUser.Region.choices:
            kb.add(KeyboardButton(label))
        await message.answer(
            "Iltimos, pastdagi tugmalardan birini tanlang (matn kiritmang) 👇",
            reply_markup=kb
        )
        return

    await state.update_data(region=region_value)
    await state.set_state(RegisterState.education.state)
    await message.answer("O‘qish joyingizni kiriting 👇", reply_markup=types.ReplyKeyboardRemove())


# 2. Education handlerdan keyin ishlaydigan yangi funksiya
async def education_handler(message: Message, state: FSMContext):
    await state.update_data(education_place=message.text.strip())
    await state.set_state(RegisterState.experience.state)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Tajribaga ega emasman")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "<b>Volontyorlik tajribangiz haqida batafsil ma'lumot bering:</b>\n\n"
        "Qaysi tashkilotlarda bo'lgansiz va nima ishlar qilgansiz? "
        "Bu biz uchun juda muhim! 👇",
        reply_markup=kb,
        parse_mode="HTML"
    )

async def experience_handler(message: Message, state: FSMContext):
    await state.update_data(experience=message.text.strip())
    await state.set_state(RegisterState.photo.state)
    await message.answer(
        "Profil rasmingizni yuklang 📸",
        reply_markup=types.ReplyKeyboardRemove()
    )

async def photo_handler(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Iltimos, rasm yuboring!")
        return

    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)

    await state.set_state(RegisterState.phone.state)
    await message.answer(
        "Telefon raqamingizni yuboring 👇",
        reply_markup=contact_btn()
    )


async def phone_handler(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("Iltimos, tugma orqali telefon raqam yuboring 👇")
        return

    # ИСПРАВЛЕНО: раньше проверка "message.contact.user_id != message.from_user.id"
    # была слишком строгой — на некоторых клиентах Telegram user_id вообще
    # не приходит (None) даже когда юзер честно жмёт кнопку "поделиться
    # своим номером", и хендлер ложно отклонял настоящий номер, из-за чего
    # выглядело, будто бот завис на этом шаге. Теперь отклоняем только если
    # user_id реально пришёл И явно не совпадает.
    if message.contact.user_id is not None and message.contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Bu boshqa odamning raqami ko'rinadi. Iltimos, faqat pastdagi "
            "tugma orqali O'ZINGIZNING raqamingizni yuboring 👇",
            reply_markup=contact_btn()
        )
        return

    data = await state.get_data()
    user_id = message.from_user.id

    new_user = TGUser(
        tg_id=user_id,
        fullname=data.get("fullname"),
        age=data.get("age"),
        username=message.from_user.username,
        email=data.get("email"),
        phone=message.contact.phone_number,
        region=data.get("region"),
        education_place=data.get("education_place"),
        experience=data.get("experience"),
    )

    # ИСПРАВЛЕНО: раньше загрузка фото ничем не была защищена — если
    # file_id устарел или Telegram на секунду не ответил, вся функция
    # падала необработанным исключением, и юзер молча зависал на этом шаге
    # без единого ответа от бота. Теперь при сбое загрузки фото регистрация
    # всё равно продолжается — просто без фото, а не рвётся насмерть.
    photo_file_id = data.get("photo_file_id")
    if photo_file_id:
        try:
            photo_buffer = BytesIO()
            await message.bot.download_file_by_id(photo_file_id, photo_buffer)
            photo_buffer.seek(0)
            photo_name = f"user_{user_id}.jpg"
            new_user.photo.save(photo_name, ContentFile(photo_buffer.read()), save=False)
        except Exception as e:
            print(f"[register] Photo download failed for tg_id={user_id}: {e}")
            # продолжаем без фото, не прерываем регистрацию целиком

    # ── аккуратная обработка дубликата email/tg_id ──
    try:
        await sync_to_async(new_user.save)()
    except IntegrityError as e:
        error_text = str(e).lower()

        if "email" in error_text:
            await state.set_state(RegisterState.email.state)
            await message.answer(
                "⚠️ Bu email allaqachon ro'yxatdan o'tgan. "
                "Iltimos, boshqa email manzilini kiriting 👇"
            )
            return

        if "tg_id" in error_text:
            await state.finish()
            await message.answer(
                "Siz allaqachon ro'yxatdan o'tgansiz ✅",
                reply_markup=reply.hi_there()
            )
            return

        raise

    await state.finish()
    await message.answer("✅ Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!", reply_markup=reply.hi_there())

# Register all handlers
def register_register(dp: Dispatcher):
    dp.register_message_handler(register_handler, lambda m: m.text == register_text, state="*")
    dp.register_message_handler(fullname_handler, state=RegisterState.fullname.state)
    dp.register_message_handler(age_handle, state=RegisterState.age.state)
    dp.register_message_handler(email_handler, state=RegisterState.email.state)
    dp.register_message_handler(region_handler, state=RegisterState.region.state)
    dp.register_message_handler(education_handler, state=RegisterState.education.state)
    dp.register_message_handler(experience_handler, state=RegisterState.experience.state)
    dp.register_message_handler(
        photo_handler,
        content_types=['photo'],
        state=RegisterState.photo.state
    )
    dp.register_message_handler(
        phone_handler,
        content_types=['contact'],
        state=RegisterState.phone.state
    )