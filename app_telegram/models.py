from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation
from ..keyboards import reply

# --- КЛАВИАТУРЫ ---

def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📅 Kelgusi tadbirlar", "📜 O'tgan tadbirlar")
    kb.row("⬅️ Orqaga")
    return kb

def get_registration_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Ro'yxatdan o'tish"))
    kb.add(KeyboardButton("⬅️ Orqaga"))
    return kb

# --- HANDLERS ---

# Главное меню эвентов
async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi.</b> ✨\n\nMarhamat, bo'limni tanlang:", 
                         reply_markup=get_events_menu(), parse_mode="HTML")

# Список БУДУЩИХ эвентов
async def list_upcoming_events(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__gte=timezone.now(), is_active=True)
    )
    
    if not projects:
        await message.answer("Hozircha yangi tadbirlar yo'q. 😔")
        return

    for p in projects:
        # Мы добавляем ID проекта в текст, чтобы бот понял, на что регистрироваться
        text = (
            f"🚀 <b>{p.title}</b>\n"
            f"ID: <code>{p.id}</code>\n\n" # Юзеру это знать не обязательно, но боту поможет
            f"📅 <b>Sana:</b> {p.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 <b>Joy:</b> {p.location_name}\n\n"
            f"📝 {p.description}"
        )
        
        if p.photo:
            try:
                await message.answer_photo(types.InputFile(p.photo.path), caption=text, 
                                           reply_markup=get_registration_kb(), parse_mode="HTML")
            except:
                await message.answer(text, reply_markup=get_registration_kb(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=get_registration_kb(), parse_mode="HTML")

# ЛОГИКА РЕГИСТРАЦИИ (Через обычную кнопку)
async def process_registration(message: types.Message, state: FSMContext):
    # Пытаемся найти последний просмотренный проект (из текста сообщения выше)
    # Но проще всего взять первый активный проект или использовать FSM
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    
    # Ищем самый свежий проект, который сейчас активен
    project = await sync_to_async(EcoProject.objects.filter(is_active=True, date__gte=timezone.now()).first)()
    
    if not project:
        await message.answer("Hozircha ro'yxatdan o'tish uchun faol loyihalar yo'q. ❌")
        return

    participation, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )
    
    if created:
        await message.answer(
            f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
            f"Loyiha: {project.title}\n"
            f"Tashkilotchilar profilingizni ko'rib chiqishadi. "
            f"Tasdiqlangach, bot sizga kanal linkini yuboradi. ⏳",
            reply_markup=get_events_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer("Siz ushbu loyihaga allaqachon ariza topshirgansiz! 😊", reply_markup=get_events_menu())

# Список ПРОШЕДШИХ эвентов
async def list_past_events(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    )
    if not projects:
        await message.answer("Tarixda hali tadbirlar yo'q. 🌳")
        return
    for p in projects:
        await message.answer(f"✅ <b>{p.title}</b>\n📅 {p.date.strftime('%d.%m.%Y')}\n\nUshbu tadbir yakunlandi.")

# Обработка секретного кода
async def handle_secret_code(message: types.Message):
    code = message.text.strip()
    project = await sync_to_async(EcoProject.objects.filter(secret_code=code, is_active=True).first)()
    
    if project:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
        part = await sync_to_async(ProjectParticipation.objects.filter(user=user, project=project).first)()
        
        if part:
            if part.status == 'attended':
                await message.answer("Siz ballarni olib bo'lgansiz! ✅")
            elif part.status == 'registered':
                part.status = 'attended'
                await sync_to_async(part.save)()
                await message.answer(f"🎉 10 ball berildi! <b>{project.title}</b>")
            else:
                await message.answer("Arizangiz hali tasdiqlanmagan. ❌")

async def back_to_main(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Asosiy menyu", reply_markup=reply.hi_there())

# --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ---
def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, text="🌱 Tadbirlar", state="*")
    dp.register_message_handler(list_upcoming_events, text="📅 Kelgusi tadbirlar", state="*")
    dp.register_message_handler(list_past_events, text="📜 O'tgan tadbirlar", state="*")
    dp.register_message_handler(back_to_main, text="⬅️ Orqaga", state="*")
    
    # Теперь ловим текстовую кнопку
    dp.register_message_handler(process_registration, text="✅ Ro'yxatdan o'tish", state="*")
    
    # Проверка кода
    dp.register_message_handler(handle_secret_code, state="*")