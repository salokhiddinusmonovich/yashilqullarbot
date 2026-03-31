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

# Меню выбора: Будущие или Прошедшие
async def show_events_menu(message: types.Message):
    await message.answer("<b>Tadbirlar bo'limi.</b>\n\nMarhamat, bo'limni tanlang: ✨", 
                         reply_markup=get_events_menu(), parse_mode="HTML")

# Список БУДУЩИХ ивентов (Upcoming)
async def list_upcoming_events(message: types.Message):
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
            f"<i>Ro'yxatdan o'ting va biz profilingizni ko'rib chiqamiz!</i>"
        )
        
        # Только кнопка регистрации. Ссылки придут после одобрения!
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("✅ Ro'yxatdan o'tish", callback_data=f"join_{p.id}"))

        if p.photo:
            await message.answer_photo(types.InputFile(p.photo.path), caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")

# Список ПРОШЕДШИХ ивентов (Past)
async def list_past_events(message: types.Message):
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')
    )
    if not projects:
        await message.answer("Tarixda hali tadbirlar yo'q. 🌳")
        return

    for p in projects:
        text = (
            f"✅ <b>{p.title}</b> (Yakunlangan)\n"
            f"📅 <b>Sana:</b> {p.date.strftime('%d.%m.%Y')}\n\n"
            f"<i>Ushbu loyiha muvaffaqiyatli amalga oshirildi!</i>"
        )
        if p.photo:
            await message.answer_photo(types.InputFile(p.photo.path), caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

# Регистрация (Статус PENDING по умолчанию)
async def join_callback(callback: types.CallbackQuery):
    project_id = callback.data.split("_")[1]
    user = await sync_to_async(TGUser.objects.get)(tg_id=callback.from_user.id)
    project = await sync_to_async(EcoProject.objects.get)(id=project_id)
    
    participation, created = await sync_to_async(ProjectParticipation.objects.get_or_create)(
        user=user, project=project
    )
    
    if created:
        text = (
            f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
            f"Sizning profilingiz tashkilotchilar tomonidan ko'rib chiqiladi. "
            f"Agar ma'lumotlaringiz to'g'ri bo'lsa, bot sizga maxsus kanal linkini yuboradi. "
            f"Iltimos, kuting! ✨"
        )
        await callback.message.answer(text, parse_mode="HTML")
    else:
        await callback.answer("Siz allaqachon ariza topshirgansiz. Javobni kuting! 😊", show_alert=True)
    
    await callback.answer()

# Прием СЕКРЕТНОГО КОДА на месте ивента
async def handle_secret_code(message: types.Message):
    code = message.text.strip()
    project = await sync_to_async(EcoProject.objects.filter(secret_code=code).first)()
    
    if project:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
        part = await sync_to_async(ProjectParticipation.objects.filter(user=user, project=project).first)()
        
        if part:
            if part.status == 'attended':
                await message.answer("Siz allaqachon ballarni olgansiz! ✨")
            elif part.status == 'registered':
                part.status = 'attended'
                await sync_to_async(part.save)()
                await message.answer(f"🎉 Tabriklaymiz! <b>{project.title}</b> uchun 10 eko-ball berildi!", parse_mode="HTML")
            else:
                await message.answer("Arizangiz hali tasdiqlanmagan yoki rad etilgan. ❗")
        else:
            await message.answer("Siz bu loyihaga ro'yxatdan o'tmagansiz. ❗")
    else:
        # Если это просто текст, не реагируем (чтобы не мешать другим командам)
        pass

async def go_back(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Asosiy menyu", reply_markup=reply.hi_there())

# --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ---
def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, text="🌱 Tadbirlar", state="*")
    dp.register_message_handler(list_upcoming_events, text="📅 Kelgusi tadbirlar", state="*")
    dp.register_message_handler(list_past_events, text="📜 O'tgan tadbirlar", state="*")
    dp.register_message_handler(go_back, text="⬅️ Orqaga", state="*")
    dp.register_callback_query_handler(join_callback, lambda c: c.data.startswith('join_'), state="*")
    dp.register_message_handler(handle_secret_code, state="*")