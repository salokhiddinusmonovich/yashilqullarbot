from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation

# --- УЛЬТРА-НАДЕЖНЫЕ КЛАВИАТУРЫ ---
def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.row(KeyboardButton("📅 Kelgusi tadbirlar"), KeyboardButton("📜 O'tgan tadbirlar"))
    kb.row(KeyboardButton("⬅️ Orqaga"))
    return kb

def get_registration_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.add(KeyboardButton("✅ Ro'yxatdan o'tish"))
    kb.add(KeyboardButton("⬅️ Orqaga"))
    return kb

# --- HANDLERS ---

# 1. Вход в меню (Очищаем всё, чтобы кнопки заработали)
async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish() # Сносим любые старые состояния!
    await message.answer("<b>Tadbirlar bo'limi</b> ✨", reply_markup=get_events_menu(), parse_mode="HTML")

# 2. Список будущих ивентов
async def list_upcoming_events(message: types.Message, state: FSMContext):
    # Фильтр: Активные и дата больше текущей
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True, date__gt=timezone.now())
    )
    
    if not projects:
        await message.answer("Hozircha yangi tadbirlar yo'q. 😔")
        return

    for p in projects:
        text = (
            f"🚀 <b>{p.title}</b>\n\n"
            f"📅 <b>Sana:</b> {p.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 <b>Joy:</b> {p.location_name}\n\n"
            f"📝 {p.description}"
        )
        await message.answer(text, reply_markup=get_registration_kb(), parse_mode="HTML")

# 3. Сама регистрация (Ловим текст кнопки)
async def process_registration(message: types.Message, state: FSMContext):
    try:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
        # Берем самый ближайший активный проект
        project = await sync_to_async(EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).first)()
        
        if not project:
            await message.answer("Ro'yxatdan o'tish uchun faol loyihalar topilmadi. ❌")
            return

        # Создаем запись
        part, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
            user=user, project=project
        )
        
        if created:
            await message.answer(
                f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
                f"Loyiha: {project.title}\n"
                f"Adminlar tasdiqlashini kuting. ✨",
                reply_markup=get_events_menu(),
                parse_mode="HTML"
            )
        else:
            await message.answer("Siz allaqachon ro'yxatdan o'tgansiz. 😊", reply_markup=get_events_menu())
            
    except Exception as e:
        print(f"Ошибка регистрации: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")

# 4. Секретный код (Если это не кнопка, проверяем на код)
async def handle_everything_else(message: types.Message, state: FSMContext):
    # Если нажали "Назад"
    if message.text == "⬅️ Orqaga":
        await state.finish()
        from ..keyboards import reply
        await message.answer("Asosiy menyu", reply_markup=reply.hi_there())
        return

    # Проверка на секретный код
    code = message.text.strip()
    project = await sync_to_async(EcoProject.objects.filter(secret_code=code, is_active=True).first)()
    
    if project:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
        part = await sync_to_async(ProjectParticipation.objects.filter(user=user, project=project).first)()
        
        if part and part.status == 'registered':
            part.status = 'attended'
            await sync_to_async(part.save)()
            await message.answer(f"🎉 Маладес! 10 ball berildi!")
        elif part and part.status == 'attended':
            await message.answer("Ball olib bo'lingan. ✅")
        else:
            await message.answer("Avval ro'yxatdan o'tishingiz kerak. ❗")

# --- РЕГИСТРАЦИЯ (ВАЖЕН ПОРЯДОК!) ---
def register_eco_clubs(dp: Dispatcher):
    # Сначала ловим конкретные кнопки
    dp.register_message_handler(show_events_menu, lambda m: "Tadbirlar" in m.text, state="*")
    dp.register_message_handler(list_upcoming_events, lambda m: "Kelgusi" in m.text, state="*")
    dp.register_message_handler(process_registration, lambda m: "Ro'yxatdan o'tish" in m.text, state="*")
    
    # В самом конце ловим всё остальное (коды, назад и т.д.)
    dp.register_message_handler(handle_everything_else, state="*")