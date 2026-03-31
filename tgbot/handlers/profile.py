from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types
from aiogram.dispatcher import FSMContext
from asgiref.sync import sync_to_async
from aiogram import Dispatcher
from app_telegram.models import TGUser
from ..keyboards import reply # Убедись, что путь к твоим главным кнопкам верный

class ProfileUpdate(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()

# --- 1. ГЛАВНОЕ МЕНЮ ПРОФИЛЯ ---
async def profile_menu(message: types.Message, state: FSMContext):
    await state.finish() # Сбрасываем всё, чтобы кнопки работали сразу
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Profilni ko'rish")
    kb.add("📸 Rasmni yangilash", "✍️ Ismni o'zgartirish")
    kb.add("⬅️ Orqaga")
    
    await message.answer(
        "👤 <b>Shaxsiy kabinet</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )

async def view_my_profile(message: types.Message):
    # 1. Получаем юзера
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    
    if not user:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz. ❗")
        return

    # 2. Получаем список посещенных ивентов (статус 'attended')
    from app_telegram.models import ProjectParticipation
    attended_projects = await sync_to_async(list)(
        ProjectParticipation.objects.filter(user=user, status='attended').select_related('project')
    )
    
    # Считаем количество
    events_count = len(attended_projects)
    
    # Формируем список названий ивентов
    projects_titles = "\n".join([f"✅ {p.project.title}" for p in attended_projects]) or "Hali tadbirlarda qatnashmadingiz 🌿"

    profile_text = (
        f"🌟 <b>SIZNING PROFILINGIZ</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏆 <b>Daraja:</b> {user.rank}\n"
        f"💰 <b>Balans:</b> {user.balance} eko-ball\n"
        f"📅 <b>Tadbirlar:</b> {events_count} ta\n" # Сколько раз пришел
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Ism:</b> {user.fullname}\n"
        f"📞 <b>Tel:</b> {user.phone}\n"
        f"📍 <b>Hudud:</b> {user.get_region_display()}\n\n"
        f"📜 <b>Ishtirok etgan tadbirlaringiz:</b>\n"
        f"{projects_titles}\n\n"
        f"🍀 <i>Yashil Qo'llar — birgalikda kuchmiz!</i>"
    )

    # Вывод фото (как в прошлом коде)
    if user.photo:
        try:
            await message.answer_photo(photo=types.InputFile(user.photo.path), caption=profile_text, parse_mode="HTML")
        except:
            await message.answer(profile_text, parse_mode="HTML")
    else:
        await message.answer(profile_text, parse_mode="HTML")

# --- 3. ИЗМЕНЕНИЕ ИМЕНИ ---
async def ask_for_name(message: types.Message):
    await message.answer("✍️ <b>Yangi ism va familiyangizni kiriting:</b>", parse_mode="HTML")
    await ProfileUpdate.waiting_for_name.set()

async def save_new_name(message: types.Message, state: FSMContext):
    new_name = message.text
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    user.fullname = new_name
    await sync_to_async(user.save)()
    
    await message.answer(f"✅ <b>Ism muvaffaqiyatli o'zgartirildi:</b> {new_name}")
    await profile_menu(message, state)

# --- 4. ИЗМЕНЕНИЕ ФОТО ---
async def ask_for_photo(message: types.Message):
    await message.answer("📸 <b>Yangi profilingiz uchun rasm yuboring:</b>", parse_mode="HTML")
    await ProfileUpdate.waiting_for_photo.set()

async def save_new_photo(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Iltimos, rasm yuboring! 📸")
        return

    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    photo = message.photo[-1]
    
    photo_name = f"users_photos/user_{user.tg_id}.jpg"
    await photo.download(destination_file=f"media/{photo_name}")
    
    user.photo = photo_name
    await sync_to_async(user.save)()
    
    await message.answer("✅ <b>Profilingiz rasmi yangilandi!</b>")
    await profile_menu(message, state)

# --- 5. КНОПКА НАЗАД (ГЛАВНОЕ МЕНЮ) ---
async def go_back_to_main(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "⬅️ Asosiy menyuga qaytdingiz", 
        reply_markup=reply.hi_there() # Вызываем твоё главное меню
    )

# --- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ---
def register_profile(dp: Dispatcher):
    # Используем state="*", чтобы эти кнопки работали ВСЕГДА
    dp.register_message_handler(profile_menu, text="👤 Mening profilim", state="*")
    dp.register_message_handler(view_my_profile, text="📄 Profilni ko'rish", state="*")
    dp.register_message_handler(ask_for_name, text="✍️ Ismni o'zgartirish", state="*")
    dp.register_message_handler(ask_for_photo, text="📸 Rasmni yangilash", state="*")
    dp.register_message_handler(go_back_to_main, text="⬅️ Orqaga", state="*")
    
    # Состояния FSM
    dp.register_message_handler(save_new_name, state=ProfileUpdate.waiting_for_name)
    dp.register_message_handler(save_new_photo, content_types=['photo'], state=ProfileUpdate.waiting_for_photo)