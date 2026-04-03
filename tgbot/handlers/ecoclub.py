from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation

# --- КЛАВИАТУРЫ ---

def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📅 Kelgusi tadbirlar"), KeyboardButton("📜 O'tgan tadbirlar"))
    kb.row(KeyboardButton("⬅️ Orqaga"))
    return kb

def get_registration_kb():
    # one_time_keyboard=True чтобы кнопка исчезала после нажатия
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("✅ Ro'yxatdan o'tish"))
    kb.add(KeyboardButton("⬅️ Orqaga"))
    return kb

# --- ЛОГИКА ---

# Главное меню раздела
async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi</b> ✨", reply_markup=get_events_menu(), parse_mode="HTML")

# БУДУЩИЕ СОБЫТИЯ (С датой и регистрацией)
async def list_upcoming_events(message: types.Message, state: FSMContext):
    # Берем проекты, которые еще не наступили (date > сейчас)
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).order_by('date')
    )
    
    if not projects:
        await message.answer("Hozircha yangi tadbirlar yo'q. 😊", reply_markup=get_events_menu())
        return

    for p in projects:
        text = (
            f"🚀 <b>{p.title}</b>\n\n"
            f"📅 <b>Sana:</b> {p.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 <b>Joy:</b> {p.location_name}\n\n"
            f"{f'📝 {p.description}' if p.description else ''}\n\n"
            f"<i>Ro'yxatdan o'tish uchun pastdagi tugmani bosing 👇</i>"
        )
        await message.answer(text, reply_markup=get_registration_kb(), parse_mode="HTML")

# ПРОШЕДШИЕ СОБЫТИЯ (Только фото и название, БЕЗ ДАТЫ)
async def list_past_events(message: types.Message):
    # Автоматически берем те, что уже прошли (date < сейчас)
    past_events = await sync_to_async(lambda: list(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    ))()

    if not past_events:
        await message.answer("📜 O'tgan tadbirlar arxivi hozircha bo'sh.")
        return

    for event in past_events:
        # УБРАНО ЧИСЛО. Только заголовок жирным.
        caption = f"<b>{event.title}</b>"
        
        # Описание выводится только если оно есть
        if event.description:
            caption += f"\n\n{event.description}"

        if event.photo:
            try:
                await message.answer_photo(
                    photo=InputFile(event.photo.path),
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Photo error: {e}")
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

# РЕГИСТРАЦИЯ НА ПРОЕКТ
async def process_registration(message: types.Message, state: FSMContext):
    try:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    except TGUser.DoesNotExist:
        await message.answer("Avval ro'yxatdan o'ting! ❌")
        return

    # Берем ближайший будущий проект
    project = await sync_to_async(EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).first)()
    
    if not project:
        await message.answer("Hozircha ro'yxatdan o'tish uchun faol loyihalar yo'q.", reply_markup=get_events_menu())
        return

    part, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )
    
    if created:
        await message.answer(
            "✅ <b>Siz muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
            "Arizangiz ko'rib chiqilmoqda, tez orada sizga xabar beramiz 😊",
            reply_markup=get_events_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer("Siz ushbu loyihaga allaqachon ariza topshirgansiz. 👍", reply_markup=get_events_menu())

# Кнопка назад
async def handle_back(message: types.Message, state: FSMContext):
    await state.finish()
    from ..keyboards import reply # Твоя главная клавиатура
    await message.answer("Asosiy menyu", reply_markup=reply.hi_there())

# --- РЕГИСТРАЦИЯ МОДУЛЯ ---

def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, lambda m: "Tadbirlar" in m.text, state="*")
    dp.register_message_handler(list_upcoming_events, lambda m: "Kelgusi" in m.text, state="*")
    dp.register_message_handler(list_past_events, lambda m: "O'tgan" in m.text, state="*")
    dp.register_message_handler(process_registration, lambda m: "Ro'yxatdan o'tish" in m.text, state="*")
    dp.register_message_handler(handle_back, lambda m: "Orqaga" in m.text, state="*")