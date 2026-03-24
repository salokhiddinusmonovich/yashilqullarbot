from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
from io import BytesIO
import qrcode
from ..keyboards import reply

from app_telegram.models import TGUser, EcoProject, ProjectParticipation

# --- KEYBOARDS ---

MAIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌱 Tadbirlar")],
        [KeyboardButton(text="👤 Mening profilim")]
    ],
    resize_keyboard=True
)

def projects_list_kb(projects):
    keyboard = []
    for project in projects:
        keyboard.append([KeyboardButton(text=f"📍 {project.title}")])
    keyboard.append([KeyboardButton(text="⬅️ Orqaga")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

PROJECT_DETAIL_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Ishtirok etish")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

# --- HANDLERS ---

# Измени функцию show_projects вот так:

async def show_projects(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True)
    )

    if not projects:
        # Создаем временную клавиатуру только с кнопкой Назад, 
        # чтобы юзер не застрял
        no_projects_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Orqaga")]],
            resize_keyboard=True
        )
        await message.answer(
            "Hozircha faol loyihalar mavjud emas. 😔",
            reply_markup=no_projects_kb  # <--- Теперь тут есть выход!
        )
        return

    await message.answer(
        "📌 Mavjud loyihalar ro‘yxati bilan tanishing:",
        reply_markup=projects_list_kb(projects)
    )
    
async def project_detail(message: types.Message, state: FSMContext):
    title = message.text.replace("📍 ", "").strip()

    try:
        project = await sync_to_async(EcoProject.objects.get)(title=title)
    except EcoProject.DoesNotExist:
        await message.answer("❌ Loyiha topilmadi.")
        return

    await state.update_data(project_id=project.id)

    text = (
        f"📌 {project.title}\n\n"
        f"📅 Sana: {project.date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📍 Joy: {project.location}\n\n"
        f"{project.description}"
    )
    # В функции project_detail замени строку вывода на эту:
    await message.answer(text, reply_markup=PROJECT_DETAIL_KB, parse_mode=None)

async def join_project(message: types.Message, state: FSMContext):
    data = await state.get_data()
    project_id = data.get("project_id")

    if not project_id:
        await message.answer("❌ Loyiha tanlanmagan.")
        return

    try:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    except TGUser.DoesNotExist:
        await message.answer("❗ Avval ro‘yxatdan o‘ting. /register")
        return

    # Tekshirish: Foydalanuvchi allaqachon a'zomi?
    participation_exists = await sync_to_async(
        ProjectParticipation.objects.filter(user=user, project_id=project_id).exists
    )()

    if participation_exists:
        await message.answer("⚠️ Siz ushbu loyihaga allaqachon a'zo bo'lgansiz!")
        return

    participation = await sync_to_async(ProjectParticipation.objects.create)(
        user=user,
        project_id=project_id
    )

    qr_text = f"Yashil Qollar | Project: {participation.project.title} | Name: {user.fullname} | ID: {user.tg_id}"
    qr_img = qrcode.make(qr_text)
    bio = BytesIO()
    qr_img.save(bio)
    bio.seek(0)

    await message.answer_photo(
        bio,
        caption=(
            "✅ Siz loyiha ishtirokchisiz!\n"
            "🎟 Ushbu QR-kodni tadbirda ko‘rsating.\n"
            "⚠️ QR faqat siz uchun amal qiladi."
        )
    )

async def go_back(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "⬅️ Asosiy menyu",
        reply_markup=reply.hi_there()
    )

# --- REGISTRATION ---

def register_eco_clubs(dp: Dispatcher):
    # "🌱 Tadbirlar" bosilganda srazu show_projects ishlaydi
    dp.register_message_handler(show_projects, lambda m: m.text == "🌱 Tadbirlar", state="*")
    
    dp.register_message_handler(project_detail, lambda m: m.text.startswith("📍 "), state="*")
    dp.register_message_handler(join_project, lambda m: m.text == "✅ Ishtirok etish", state="*")
    dp.register_message_handler(go_back, lambda m: m.text == "⬅️ Orqaga", state="*")