from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from asgiref.sync import sync_to_async
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation

# --- КНОПКИ ---

def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📅 Kelgusi tadbirlar"), KeyboardButton("📜 O'tgan tadbirlar"))
    kb.row(KeyboardButton("⬅️ Orqaga"))
    return kb

def get_registration_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("✅ Ro'yxatdan o'tish"))
    kb.add(KeyboardButton("⬅️ Orqaga"))
    return kb

# --- ЛОГИКА ---

async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi</b> ✨", reply_markup=get_events_menu(), parse_mode="HTML")

async def list_past_events(message: types.Message):
    # Мы берем ВСЕ проекты, у которых is_past=True, независимо от их активности
    past_events = await sync_to_async(lambda: list(
        EcoProject.objects.filter(is_past=True).order_by('-date') 
    ))()

    if not past_events:
        await message.answer("📜 O'tgan tadbirlar arxivi hozircha bo'sh.")
        return

    for event in past_events:
        # Убираем число, оставляем только имя (как ты просил)
        caption = f"<b>{event.title}</b>"
        
        # Описание опционально
        if event.description:
            caption += f"\n\n{event.description}"

        if event.photo:
            try:
                # Проверь, что путь к фото корректный
                await message.answer_photo(
                    photo=InputFile(event.photo.path),
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as e:
                # Если фото не грузится (например, удалено с сервера), шлем текст
                print(f"Ошибка фото: {e}")
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")
    
async def process_registration(message: types.Message, state: FSMContext):
    try:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    except TGUser.DoesNotExist:
        await message.answer("Avval ro'yxatdan o'ting! ❌")
        return

    project = await sync_to_async(EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).first)()
    
    if not project:
        await message.answer("Xatolik: Loyiha topilmadi. ❌", reply_markup=get_events_menu())
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

# ИСПРАВЛЕННАЯ ФУНКЦИЯ (убрано event_date)
async def list_past_events(message: types.Message):
    # ВАЖНО: убедись, что поле в модели называется 'date' или исправь на свое
    past_events = await sync_to_async(lambda: list(
        EcoProject.objects.filter(is_past=True).order_by('-date') # Было event_date
    ))()

    if not past_events:
        await message.answer("Hozircha o'tgan tadbirlar mavjud emas.")
        return

    for event in past_events:
        caption = f"<b>{event.title}</b>"
        
        # Описание теперь опциональное (как ты просил)
        if event.description:
            caption += f"\n\n{event.description}"

        if event.photo:
            try:
                # Отправляем фото по пути из медиа-папки
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

async def handle_back(message: types.Message, state: FSMContext):
    await state.finish()
    from ..keyboards import reply
    await message.answer("Asosiy menyu", reply_markup=reply.hi_there())

# --- РЕГИСТРАЦИЯ ---

def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, lambda m: "Tadbirlar" in m.text, state="*")
    dp.register_message_handler(list_upcoming_events, lambda m: "Kelgusi" in m.text, state="*")
    dp.register_message_handler(list_past_events, lambda m: "O'tgan" in m.text, state="*")
    dp.register_message_handler(process_registration, lambda m: "Ro'yxatdan o'tish" in m.text, state="*")
    dp.register_message_handler(handle_back, lambda m: "Orqaga" in m.text, state="*")