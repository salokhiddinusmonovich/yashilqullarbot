from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types
from aiogram.dispatcher import FSMContext
from asgiref.sync import sync_to_async
from aiogram import Dispatcher
from app_telegram.models import TGUser

class ProfileUpdate(StatesGroup):
    waiting_for_name = State()
    waiting_for_photo = State()


# --- 1. ГЛАВНОЕ МЕНЮ ПРОФИЛЯ ---
async def profile_menu(message: types.Message):
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

# --- 2. ПРОСМОТР ПРОФИЛЯ ---
async def view_my_profile(message: types.Message):
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    
    if not user:
        await message.answer("Ro'yxatdan o'ting: /start")
        return

    profile_text = (
        f"🌟 <b>SIZNING PROFILINGIZ</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏆 <b>Daraja:</b> {user.rank}\n"
        f"💰 <b>Balans:</b> {user.balance} eko-ball\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Ism:</b> {user.fullname}\n"
        f"📞 <b>Tel:</b> {user.phone}\n"
        f"📍 <b>Hudud:</b> {user.get_region_display()}\n\n"
        f"🍀 <i>Yashil Qo'llar loyihasi</i>"
    )

    if user.photo:
        try:
            with open(user.photo.path, 'rb') as photo:
                await message.answer_photo(photo=photo, caption=profile_text, parse_mode="HTML")
        except:
            await message.answer(profile_text, parse_mode="HTML")
    else:
        await message.answer(profile_text, parse_mode="HTML")

# --- 3. ИЗМЕНЕНИЕ ФОТО (ЛОГИКА) ---
async def ask_for_photo(message: types.Message):
    await message.answer("📸 <b>Yangi profilingiz uchun rasm yuboring:</b>", parse_mode="HTML")
    await ProfileUpdate.waiting_for_photo.set()

async def save_new_photo(message: types.ContentType.PHOTO, state: FSMContext):
    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    
    # Сохраняем фото на сервер
    photo = message.photo[-1]
    photo_path = f"media/users_photos/user_{user.tg_id}.jpg"
    await photo.download(destination_file=photo_path)
    
    # Обновляем в базе
    user.photo = f"users_photos/user_{user.tg_id}.jpg"
    await sync_to_async(user.save)()
    
    await message.answer("✅ <b>Profilingiz rasmi muvaffaqiyatli yangilandi!</b>", parse_mode="HTML")
    await state.finish()
    await profile_menu(message)

# --- РЕГИСТРАЦИЯ ВСЕХ КНОПОК ---
def register_profile(dp: Dispatcher):
    # Основная кнопка
    dp.register_message_handler(profile_menu, text="👤 Mening profilim", state="*")
    
    # Кнопка Просмотра
    dp.register_message_handler(view_my_profile, text="📄 Profilni ko'rish", state="*")
    
    # Кнопка Изменения фото
    dp.register_message_handler(ask_for_photo, text="📸 Rasmni yangilash", state="*")
    
    # Хендлер, который ловит само ФОТО
    dp.register_message_handler(save_new_photo, content_types=['photo'], state=ProfileUpdate.waiting_for_photo)

    # Назад
    dp.register_message_handler(lambda m: m.text == "⬅️ Orqaga", text="⬅️ Orqaga", state="*")