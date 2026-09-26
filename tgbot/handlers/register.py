import logging
import re
from io import BytesIO

from aiogram import Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from django.db import IntegrityError

from app_telegram.models import TGUser
from tgbot.i18n import t, variants, region_from_text
from ..keyboards import reply
from ..keyboards.reply import contact_btn, region_kb
from .link_account import offer_link
from .help import send_guide

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[\w\.+-]+@[\w\.-]+\.\w+$")


class RegisterState(StatesGroup):
    fullname = State()
    age = State()
    email = State()
    region = State()
    education = State()
    experience = State()
    photo = State()
    phone = State()


# Шаг 1: имя
async def register_handler(message: Message, state: FSMContext):
    await state.set_state(RegisterState.fullname.state)
    await message.answer(t("reg_ask_name"), reply_markup=types.ReplyKeyboardRemove())


async def fullname_handler(message: Message, state: FSMContext):
    await state.update_data(fullname=message.text.strip())
    await state.set_state(RegisterState.age.state)
    await message.answer(t("reg_ask_age"))


# Шаг 2: возраст
async def age_handle(message: Message, state: FSMContext):
    age_str = message.text.strip()
    if not age_str.isdigit() or not (5 <= int(age_str) <= 120):
        await message.answer(t("reg_bad_age"))
        return
    await state.update_data(age=int(age_str))
    await state.set_state(RegisterState.email.state)
    await message.answer(t("reg_ask_email"))


# Шаг 3: email
async def email_handler(message: Message, state: FSMContext):
    email = message.text.strip().lower()
    if not EMAIL_REGEX.match(email):
        await message.answer(t("reg_bad_email"))
        return

    # Email уже есть в базе (чаще всего — зарегистрировался на сайте):
    # не гоним человека по всей анкете до "email band" в самом конце,
    # а сразу предлагаем привязать существующий аккаунт.
    existing = await sync_to_async(TGUser.objects.filter(email__iexact=email).first)()
    if existing:
        await offer_link(message, state, existing)
        return

    await state.update_data(email=email)
    await state.set_state(RegisterState.region.state)
    await message.answer(t("reg_ask_region"), reply_markup=region_kb())


# Шаг 4: регион — только кнопкой. Произвольный текст раньше давал в базе
# "Toshkent shahri", "Toshkent  shahri", "Tashkent shahar" и т.д. —
# ни один не совпадал с реальным кодом региона.
async def region_handler(message: Message, state: FSMContext):
    region_value = region_from_text(message.text)
    if not region_value:
        await message.answer(t("use_buttons"), reply_markup=region_kb())
        return

    await state.update_data(region=region_value)
    await state.set_state(RegisterState.education.state)
    await message.answer(t("reg_ask_education"), reply_markup=types.ReplyKeyboardRemove())


# Шаг 5: учёба
async def education_handler(message: Message, state: FSMContext):
    await state.update_data(education_place=message.text.strip())
    await state.set_state(RegisterState.experience.state)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("btn_no_experience"))]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(t("reg_ask_experience"), reply_markup=kb)


# Шаг 6: опыт
async def experience_handler(message: Message, state: FSMContext):
    await state.update_data(experience=message.text.strip())
    await state.set_state(RegisterState.photo.state)
    await message.answer(t("reg_ask_photo"), reply_markup=types.ReplyKeyboardRemove())


# Шаг 7: фото
async def photo_handler(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer(t("send_photo"))
        return

    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(RegisterState.phone.state)
    await message.answer(t("reg_ask_phone"), reply_markup=contact_btn())


async def photo_expected(message: Message):
    await message.answer(t("send_photo"))


# Шаг 8: телефон → сохраняем
async def phone_handler(message: Message, state: FSMContext):
    # Отклоняем только если user_id реально пришёл И не совпадает: на
    # некоторых клиентах Telegram его вообще не присылает (None) даже
    # для своего номера.
    if message.contact.user_id is not None and message.contact.user_id != message.from_user.id:
        await message.answer(t("reg_other_phone"), reply_markup=contact_btn())
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

    # Сбой загрузки фото не должен рвать регистрацию — сохраняем без фото.
    photo_file_id = data.get("photo_file_id")
    if photo_file_id:
        try:
            photo_buffer = BytesIO()
            await message.bot.download_file_by_id(photo_file_id, photo_buffer)
            photo_buffer.seek(0)
            new_user.photo.save(f"user_{user_id}.jpg", ContentFile(photo_buffer.read()), save=False)
        except Exception as e:
            logger.warning("[register] Photo download failed for tg_id=%s: %s", user_id, e)

    try:
        await sync_to_async(new_user.save)()
    except IntegrityError as e:
        error_text = str(e).lower()

        if "email" in error_text:
            # Кто-то занял этот email, пока юзер заполнял анкету —
            # предлагаем привязку, как и на шаге email.
            existing = await sync_to_async(TGUser.objects.filter(email__iexact=new_user.email).first)()
            if existing:
                await offer_link(message, state, existing)
                return
            await state.set_state(RegisterState.email.state)
            await message.answer(t("reg_email_taken"))
            return

        if "tg_id" in error_text:
            await state.finish()
            await message.answer(t("reg_already"), reply_markup=await reply.main_menu(user_id))
            return

        raise

    await state.finish()
    await message.answer(t("reg_done"), reply_markup=reply.hi_there())
    await send_guide(message)


async def phone_expected(message: Message):
    await message.answer(t("phone_use_button"), reply_markup=contact_btn())


def register_register(dp: Dispatcher):
    dp.register_message_handler(register_handler, text=variants("btn_register"), state="*")
    dp.register_message_handler(fullname_handler, state=RegisterState.fullname.state)
    dp.register_message_handler(age_handle, state=RegisterState.age.state)
    dp.register_message_handler(email_handler, state=RegisterState.email.state)
    dp.register_message_handler(region_handler, state=RegisterState.region.state)
    dp.register_message_handler(education_handler, state=RegisterState.education.state)
    dp.register_message_handler(experience_handler, state=RegisterState.experience.state)
    dp.register_message_handler(photo_handler, content_types=['photo'], state=RegisterState.photo.state)
    dp.register_message_handler(photo_expected, state=RegisterState.photo.state)
    dp.register_message_handler(phone_handler, content_types=['contact'], state=RegisterState.phone.state)
    dp.register_message_handler(phone_expected, state=RegisterState.phone.state)
