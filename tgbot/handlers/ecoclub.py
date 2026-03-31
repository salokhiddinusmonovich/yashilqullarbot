from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation

# --- ТВОИ КНОПКИ ---

def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📅 Kelgusi tadbirlar"), KeyboardButton("📜 O'tgan tadbirlar"))
    kb.row(KeyboardButton("⬅️ Orqaga"))
    return kb

def get_registration_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Ro'yxatdan o'tish"))
    kb.add(KeyboardButton("⬅️ Orqaga"))
    return kb

# --- ЛОГИКА ---

async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi</b> ✨", reply_markup=get_events_menu(), parse_mode="HTML")

async def list_upcoming_events(message: types.Message, state: FSMContext):
    # Берем только активные будущие проекты
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True, date__gt=timezone.now())
    )
    
    if not projects:
        await message.answer("Hozircha yangi tadbirlar yo'q. 😔", reply_markup=get_events_menu())
        return

    for p in projects:
        text = (
            f"🚀 <b>{p.title}</b>\n\n"
            f"📅 <b>Sana:</b> {p.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 <b>Joy:</b> {p.location_name}\n\n"
            f"📝 {p.description}\n\n"
            f"<i>Ro'yxatdan o'tish uchun pastdagi tugmani bosing 👇</i>"
        )
        # Сразу даем кнопку регистрации под каждым проектом
        await message.answer(text, reply_markup=get_registration_kb(), parse_mode="HTML")

async def process_registration(message: types.Message, state: FSMContext):
    # Ищем юзера в твоей новой модели (через tg_id)
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    # Берем самый актуальный проект
    project = await sync_to_async(EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).first)()
    
    if not project:
        await message.answer("Xatolik: Loyiha topilmadi. ❌", reply_markup=get_events_menu())
        return

    # Записываем в базу
    part, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )
    
    if created:
        # ТОТ САМЫЙ ОТВЕТ, КОТОРЫЙ ТЫ ПРОСИЛ:
        await message.answer(
            "✅ <b>Siz muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
            "Biz arizangizni ko'rib chiqamiz va tez orada o'zimiz siz bilan bog'lanamiz. "
            "Hozircha kutib turing. 😊",
            reply_markup=get_events_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer("Siz ushbu loyihaga allaqachon ariza topshirgansiz. 👍", reply_markup=get_events_menu())

async def list_past_events(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    )
    if not projects:
        await message.answer("Tarixda hali tadbirlar yo'q. 🌳")
        return

    for p in projects:
        await message.answer(f"✅ <b>{p.title}</b>\n📅 {p.date.strftime('%d.%m.%Y')}\n\nTadbir yakunlangan.")

async def handle_back(message: types.Message, state: FSMContext):
    if "Orqaga" in message.text:
        await state.finish()
        from ..keyboards import reply
        await message.answer("Asosiy menyu", reply_markup=reply.hi_there())

# --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ---

def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, lambda m: "Tadbirlar" in m.text, state="*")
    dp.register_message_handler(list_upcoming_events, lambda m: "Kelgusi" in m.text, state="*")
    dp.register_message_handler(list_past_events, lambda m: "O'tgan" in m.text, state="*")
    dp.register_message_handler(process_registration, lambda m: "Ro'yxatdan o'tish" in m.text, state="*")
    dp.register_message_handler(handle_back, lambda m: "Orqaga" in m.text, state="*")