from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation

# --- ПРОСТЫЕ КЛАВИАТУРЫ ---

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

# --- HANDLERS ---

# Главное меню
async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi</b> ✨\n\nBo'limni tanlang:", 
                         reply_markup=get_events_menu(), parse_mode="HTML")

# Список будущих мероприятий
async def list_upcoming_events(message: types.Message, state: FSMContext):
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
        await message.answer(text, reply_markup=get_registration_kb(), parse_mode="HTML")

# Регистрация (Простая логика: Записали в базу -> Ответили юзеру)
async def process_registration(message: types.Message, state: FSMContext):
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    # Берем ближайший активный проект
    project = await sync_to_async(EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).first)()
    
    if not project:
        await message.answer("Xatolik: Faol loyihalar topilmadi. ❌", reply_markup=get_events_menu())
        return

    # Создаем запись в базе (по умолчанию статус 'pending' в модели)
    part, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )
    
    if created:
        # Ответ на узбекском, как ты просил
        await message.answer(
            f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
            f"Loyiha: {project.title}\n"
            f"Biz sizning profilingizni ko'rib chiqamiz va tez orada o'zimiz aloqaga chiqamiz. "
            f"Iltimos, kuting! ✨",
            reply_markup=get_events_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz! 😊", reply_markup=get_events_menu())

# Прошедшие мероприятия
async def list_past_events(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    )
    if not projects:
        await message.answer("Tarixda hali tadbirlar yo'q. 🌳")
        return

    for p in projects:
        text = f"✅ <b>{p.title}</b>\n📅 {p.date.strftime('%d.%m.%Y')}\n\nTadbir yakunlangan."
        await message.answer(text, parse_mode="HTML")

# Обработка "Назад" и прочего текста
async def handle_eco_logic(message: types.Message, state: FSMContext):
    if "Orqaga" in message.text:
        await state.finish()
        from ..keyboards import reply
        await message.answer("Asosiy menyu", reply_markup=reply.hi_there())
    else:
        # Если юзер просто что-то пишет в этом меню, ничего не делаем или даем подсказку
        pass

# --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ---
def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, lambda m: "Tadbirlar" in m.text, state="*")
    dp.register_message_handler(list_upcoming_events, lambda m: "Kelgusi" in m.text, state="*")
    dp.register_message_handler(list_past_events, lambda m: "O'tgan" in m.text, state="*")
    dp.register_message_handler(process_registration, lambda m: "Ro'yxatdan o'tish" in m.text, state="*")
    dp.register_message_handler(handle_eco_logic, state="*")