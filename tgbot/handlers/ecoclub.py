from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
from io import BytesIO
import qrcode
from  ..keyboards import reply

from app_telegram.models import TGUser
from app_telegram.models import EcoProject, ProjectParticipation


MAIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌱 Eco-klublar")],
        [KeyboardButton(text="👤 Mening profilim")]
    ],
    resize_keyboard=True
)

ECO_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Loyihalar")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)




def projects_list_kb(projects):
    keyboard = []

    for project in projects:
        keyboard.append(
            [KeyboardButton(text=f"📍 {project.title}")]
        )

    keyboard.append([KeyboardButton(text="⬅️ Orqaga")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )




PROJECT_DETAIL_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Ishtirok etish")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)


async def eco_clubs(message: types.Message):
    await message.answer(
        "🌱 Eco-klublarga xush kelibsiz!",
        reply_markup=ECO_MENU_KB
    )


async def show_projects(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True)
    )

    if not projects:
        await message.answer(
            "Hozircha loyihalar yo‘q.",
            reply_markup=ECO_MENU_KB
        )
        return

    await message.answer(
        "📌 Mavjud loyihalar:",
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

    await message.answer(text, reply_markup=PROJECT_DETAIL_KB)




# Пример join_project
import qrcode
from io import BytesIO
from asgiref.sync import sync_to_async

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

    participation, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
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



def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(
    eco_clubs,
    lambda m: m.text == "🌱 Eko klublar",
    state="*"
)


    dp.register_message_handler(
        show_projects,
        lambda m: m.text == "📌 Loyihalar",
        state="*"
    )

    dp.register_message_handler(
        project_detail,
        lambda m: m.text.startswith("📍 "),
        state="*"
    )

    dp.register_message_handler(
        join_project,
        lambda m: m.text == "✅ Ishtirok etish",
        state="*"
    )

    dp.register_message_handler(
        go_back,
        lambda m: m.text == "⬅️ Orqaga",
        state="*"
    )
