from aiogram import Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from asgiref.sync import sync_to_async
import re

from ..keyboards.text import register_text
from ..keyboards.reply import contact_btn
from ..keyboards import reply
from app_telegram.models import TGUser

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


# FSM States
class RegisterState(StatesGroup):
    fullname = State()
    age = State()
    email = State()
    region = State()
    education = State()
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
    # можно добавить несколько кнопок популярных регионов для удобства
    for value, label in TGUser.Region.choices:
        kb.add(KeyboardButton(label))

    await state.set_state(RegisterState.region.state)
    await message.answer("Qaysi hududdansiz? (shahar yoki viloyat nomini kiriting)", reply_markup=kb)


# Step 4: Region text handler
async def region_handler(message: Message, state: FSMContext):
    await state.update_data(region=message.text.strip())
    await state.set_state(RegisterState.education.state)
    await message.answer("O‘qish joyingizni kiriting 👇", reply_markup=None)


# Step 5: Education
async def education_handler(message: Message, state: FSMContext):
    await state.update_data(education_place=message.text.strip())
    await state.set_state(RegisterState.phone.state)
    await message.answer(
        "Quyidagi tugmani bosib telefon raqamingizni yuboring 👇",
        reply_markup=contact_btn()
    )


# Step 6: Phone + Create User
async def phone_handler(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("Iltimos, tugma orqali telefon raqam yuboring 👇")
        return

    phone = message.contact.phone_number
    data = await state.get_data()

    existing = await sync_to_async(
        TGUser.objects.filter(tg_id=message.from_user.id).exists
    )()
    if existing:
        await state.finish()
        await message.answer("Siz allaqachon ro‘yxatdan o‘tgansiz ✅")
        return

    await sync_to_async(TGUser.objects.create)(
        tg_id=message.from_user.id,
        fullname=data.get("fullname"),
        age=data.get("age"),
        email=data.get("email"),
        phone=phone,
        region=data.get("region"),
        education_place=data.get("education_place"),
    )

    await state.finish()
    await message.answer(
        "✅ Ro‘yxatdan o‘tish yakunlandi",
        reply_markup=reply.hi_there()
    )


# Register all handlers
def register_register(dp: Dispatcher):
    # Step 1
    dp.register_message_handler(register_handler, lambda m: m.text == register_text, state="*")
    dp.register_message_handler(fullname_handler, state=RegisterState.fullname.state)

    # Step 2
    dp.register_message_handler(age_handle, state=RegisterState.age.state)

    # Step 3
    dp.register_message_handler(email_handler, state=RegisterState.email.state)

    # Step 4
    dp.register_message_handler(region_handler, state=RegisterState.region.state)

    # Step 5
    dp.register_message_handler(education_handler, state=RegisterState.education.state)

    # Step 6
    dp.register_message_handler(
        phone_handler,
        state=RegisterState.phone.state,
        content_types=['contact']
    )
