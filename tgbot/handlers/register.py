from aiogram import Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from asgiref.sync import sync_to_async
import re


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
    # можно добавить несколько кнопок популярных регионов для удобства
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
    
    # Если нажали кнопку, сохраняем ключ. Если просто написали текст - сохраняем текст.
    final_region = region_value if region_value else selected_label
    
    await state.update_data(region=final_region)
    await state.set_state(RegisterState.education.state)
    await message.answer("O‘qish joyingizni kiriting 👇", reply_markup=types.ReplyKeyboardRemove())


# 2. Education handlerdan keyin ishlaydigan yangi funksiya
async def education_handler(message: Message, state: FSMContext):
    await state.update_data(education_place=message.text.strip())
    await state.set_state(RegisterState.experience.state)
    
    # Кнопка для тех, у кого нет опыта
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
    # Сохраняем текст опыта
    await state.update_data(experience=message.text.strip())
    
    # Переходим к следующему состоянию
    await state.set_state(RegisterState.photo.state)
    
    # ИСПРАВЛЕНИЕ: Добавляем ReplyKeyboardRemove, чтобы кнопка исчезла
    await message.answer(
        "Profil rasmingizni yuklang 📸", 
        reply_markup=types.ReplyKeyboardRemove()
    )

async def photo_handler(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Iltimos, rasm yuboring!")
        return

    # Eng katta hajmli rasmni olish
    photo = message.photo[-1]
    
    # Faqat file_id ni saqlaymiz (bu oddiy string, Redis buni yaxshi ko'radi)
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

    data = await state.get_data()
    user_id = message.from_user.id
    
    # 1. Yangi foydalanuvchi obyektini yaratish
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

    # 2. Rasmni yuklab olish (agar file_id bo'lsa)
    photo_file_id = data.get("photo_file_id")
    if photo_file_id:
        # Telegramdan rasmni yuklab olish
        photo_buffer = BytesIO()
        await message.bot.download_file_by_id(photo_file_id, photo_buffer)
        photo_buffer.seek(0)
        
        # Django modeliga saqlash
        photo_name = f"user_{user_id}.jpg"
        new_user.photo.save(photo_name, ContentFile(photo_buffer.read()), save=False)

    # 3. Bazaga saqlash
    await sync_to_async(new_user.save)()

    await state.finish()
    await message.answer("✅ Ro‘yxatdan o‘tish muvaffaqiyatli yakunlandi!", reply_markup=reply.hi_there())

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


    dp.register_message_handler(education_handler, state=RegisterState.education.state)
    
    # Step 5.5: Yangi tajriba handleri
    dp.register_message_handler(experience_handler, state=RegisterState.experience.state)

   # Step: Photo
    dp.register_message_handler(
        photo_handler, 
        content_types=['photo'], 
        state=RegisterState.photo.state
    )

    # Step: Phone
    dp.register_message_handler(
        phone_handler,
        content_types=['contact'],
        state=RegisterState.phone.state
    )