from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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

# --- HANDLERS ---

async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("<b>Tadbirlar bo'limi.</b> ✨\n\nMarhamat, bo'limni tanlang:", 
                         reply_markup=get_events_menu(), parse_mode="HTML")

async def list_upcoming_events(message: types.Message):
    # Показываем только активные будущие ивенты
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__gte=timezone.now(), is_active=True)
    )
    
    if not projects:
        await message.answer("Hozircha yangi tadbirlar yo'q. 😔")
        return

    for p in projects:
        text = (
            f"🚀 <b>{p.title}</b>\n\n"
            f"📅 <b>Sana:</b> {p.date.strftime('%d.%m.%Y %H:%M')}\n"
            f"📍 <b>Joy:</b> {p.location_name}\n\n"
            f"📝 {p.description}\n\n"
            f"<i>Ro'yxatdan o'ting, biz arizangizni ko'rib chiqamiz.</i>"
        )
        
        kb = InlineKeyboardMarkup()
        # Короткий префикс 'ev_' чтобы избежать ошибок длины callback_data
        kb.add(InlineKeyboardButton("✅ Ro'yxatdan o'tish", callback_data=f"ev_{p.id}"))

        if p.photo:
            try:
                await message.answer_photo(types.InputFile(p.photo.path), caption=text, reply_markup=kb, parse_mode="HTML")
            except:
                await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")

# ОБРАБОТКА НАЖАТИЯ КНОПКИ (ИСПРАВЛЕНО)
async def process_event_registration(callback: types.CallbackQuery):
    project_id = callback.data.replace("ev_", "")
    
    user = await sync_to_async(TGUser.objects.get)(tg_id=callback.from_user.id)
    project = await sync_to_async(EcoProject.objects.get)(id=project_id)
    
    # Создаем запись со статусом 'pending' (кутилмокда)
    participation, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )
    
    if created:
        await callback.message.answer(
            f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
            f"Tashkilotchilar profilingizni tekshirishmoqda. "
            f"Tasdiqlangach, bot sizga kanal linkini va manzilni yuboradi. "
            f"Iltimos, kuting! ⏳",
            parse_mode="HTML"
        )
    else:
        await callback.answer("Siz allaqachon ariza topshirgansiz! 😊", show_alert=True)
    
    await callback.answer()

# ПРОВЕРКА КОДА (Начисление баллов)
async def check_secret_code(message: types.Message):
    code = message.text.strip()
    # Ищем проект, где этот код совпадает
    project = await sync_to_async(EcoProject.objects.filter(secret_code=code, is_active=True).first)()
    
    if project:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
        part = await sync_to_async(ProjectParticipation.objects.filter(user=user, project=project).first)()
        
        if part:
            if part.status == 'attended':
                await message.answer("Siz bu tadbir uchun ball olib bo'lgansiz! ✅")
            elif part.status == 'registered': # Если он был одобрен
                part.status = 'attended'
                await sync_to_async(part.save)()
                await message.answer(f"🎉 <b>Ajoyib!</b>\n{project.title} uchun 10 ball berildi!", parse_mode="HTML")
            else:
                await message.answer("Arizangiz hali tasdiqlanmagan, shuning uchun ball berilmaydi. ❌")
        else:
            await message.answer("Siz bu tadbirga ro'yxatdan o'tmagansiz! ❗")

async def list_past_events(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    )
    if not projects:
        await message.answer("Tarixda hali tadbirlar yo'q. 🌳")
        return
    for p in projects:
        await message.answer(f"✅ <b>{p.title}</b>\n📅 {p.date.strftime('%d.%m.%Y')}\n\nUshbu tadbir yakunlandi.")

async def back_to_main(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Asosiy menyu", reply_markup=reply.hi_there())

def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, text="🌱 Tadbirlar", state="*")
    dp.register_message_handler(list_upcoming_events, text="📅 Kelgusi tadbirlar", state="*")
    dp.register_message_handler(list_past_events, text="📜 O'tgan tadbirlar", state="*")
    dp.register_message_handler(back_to_main, text="⬅️ Orqaga", state="*")
    
    # Самое важное: регистрация колбэка
    dp.register_callback_query_handler(process_event_registration, lambda c: c.data.startswith('ev_'), state="*")
    
    # Слушаем секретный код
    dp.register_message_handler(check_secret_code, state="*")