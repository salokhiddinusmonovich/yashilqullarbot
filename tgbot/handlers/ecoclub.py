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


async def list_upcoming_events(message: types.Message, state: FSMContext):
    # 1. Получаем пользователя, чтобы знать его регион
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    
    # 2. Берем все активные будущие проекты
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).order_by('date')
    )
    
    if not projects:
        await message.answer("Hozircha yangi tadbirlar yo'q. 😊", reply_markup=get_events_menu())
        return

    for p in projects:
        # ЗАГОЛОВОК И ОПИСАНИЕ (Показываем всем!)
        text = f"🚀 <b>{p.title}</b>\n\n"
        
        if p.description:
            text += f"{p.description}\n\n"
        
        # 3. ПРОВЕРКА РЕГИОНА
        # Предполагаем, что в EcoProject есть поле region. 
        # Если его нет, добавь его в models.py (как мы обсуждали выше)
        
        project_region = getattr(p, 'region', 'tashkent_s') # по умолчанию Ташкент

        if user.region == project_region:
            # ЕСЛИ РЕГИОН СОВПАДАЕТ: Показываем кнопку регистрации
            text += f"<i>Ro'yxatdan o'tish uchun pastdagi tugmani bosing 👇</i>"
            kb = get_registration_kb()
        else:
            # ЕСЛИ РЕГИОН ДРУГОЙ: Пишем предупреждение и НЕ ДАЕМ кнопку регистрации
            user_reg_name = dict(TGUser.Region.choices).get(user.region, user.region)
            text += (
                f"⚠️ <b>Diqqat:</b> Siz <b>{user_reg_name}</b> hududidansiz.\n"
                f"Ushbu tadbirda faqat mahalliy ko'ngillilar qatnasha oladi. "
                f"Tez orada sizning hududingizda ham tadbir o'tkazamiz! 🌱"
            )
            kb = get_events_menu() # Просто возвращаем обычное меню (без кнопки регистрации)

        # Отправка (с фото или без)
        if p.photo:
            try:
                await message.answer_photo(
                    photo=InputFile(p.photo.path),
                    caption=text,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception:
                await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")

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