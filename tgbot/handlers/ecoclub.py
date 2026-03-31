from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("✅ Ro'yxatdan o'tish")) 
    kb.add(KeyboardButton("⬅️ Orqaga"))
    return kb

# --- HANDLERS ---

async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi</b> ✨", reply_markup=get_events_menu(), parse_mode="HTML")

# ВОТ ЭТА ФУНКЦИЯ БЫЛА УДАЛЕНА:
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

# Список ПРОШЕДШИХ эвентов
async def list_past_events(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    )
    
    if not projects:
        await message.answer("Tarixda hali tadbirlar yo'q. 🌳")
        return

    for p in projects:
        text = (
            f"✅ <b>{p.title}</b>\n"
            f"📅 <b>Sana:</b> {p.date.strftime('%d.%m.%Y')}\n\n"
            f"<i>Ushbu tadbir muvaffaqiyatli yakunlangan.</i>"
        )
        
        if p.photo:
            try:
                await message.answer_photo(types.InputFile(p.photo.path), caption=text, parse_mode="HTML")
            except Exception:
                await message.answer(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

async def process_registration(message: types.Message, state: FSMContext):
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    project = await sync_to_async(EcoProject.objects.filter(is_active=True, date__gt=timezone.now()).first)()
    
    if not project:
        await message.answer("Loyihalar topilmadi. ❌", reply_markup=get_events_menu())
        return

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
        await message.answer("Siz allaqachon ro'yxatdan o'tgansiz! 😊", reply_markup=get_events_menu())

async def handle_everything(message: types.Message, state: FSMContext):
    if "Orqaga" in message.text:
        await state.finish()
        from ..keyboards import reply
        await message.answer("Asosiy menyu", reply_markup=reply.hi_there())
        return
    
    code = message.text.strip()
    project = await sync_to_async(EcoProject.objects.filter(secret_code=code, is_active=True).first)()
    if project:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
        part = await sync_to_async(ProjectParticipation.objects.filter(user=user, project=project).first)()
        if part and part.status == 'registered':
            part.status = 'attended'
            await sync_to_async(part.save)()
            await message.answer("🎉 10 ball berildi!")
        elif part and part.status == 'attended':
            await message.answer("Ball olib bo'lingan. ✅")
        else:
            await message.answer("Siz hali tasdiqlanmagansiz. ❌")

# --- РЕГИСТРАЦИЯ ---
def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, lambda m: "Tadbirlar" in m.text, state="*")
    dp.register_message_handler(list_upcoming_events, lambda m: "Kelgusi" in m.text, state="*")
    dp.register_message_handler(list_past_events, lambda m: "O'tgan" in m.text, state="*") # Добавил сюда хендлер для прошедших
    dp.register_message_handler(process_registration, lambda m: "Ro'yxatdan o'tish" in m.text, state="*")
    dp.register_message_handler(handle_everything, state="*")