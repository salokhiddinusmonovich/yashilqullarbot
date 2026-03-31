from aiogram import types
from asgiref.sync import sync_to_async
from aiogram import Dispatcher
from app_telegram.models import TGUser
from ..keyboards import reply # Твои основные кнопки

# 1. Функция, которая показывает меню профиля (3 кнопки)
async def profile_menu(message: types.Message):
    # Создаем клавиатуру выбора
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📄 Profilni ko'rish")],
            [types.KeyboardButton(text="🔄 Ma'lumotlarni yangilash")],
            [types.KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "👤 <b>Shaxsiy kabinetga xush kelibsiz!</b>\n\n"
        "Bu yerda siz o'z ma'lumotlaringizni ko'rishingiz, "
        "balansingizni tekshirishingiz yoki profilingizni tahrirlashingiz mumkin. ✨",
        reply_markup=kb,
        parse_mode="HTML"
    )

# 2. Функция, которая показывает сами данные (📄 Profilni ko'rish)
async def view_my_profile(message: types.Message):
    try:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    except TGUser.DoesNotExist:
        await message.answer("Siz hali ro‘yxatdan o‘tmagansiz. ❗")
        return

    profile_text = (
        f"🌟 <b>SIZNING PROFILINGIZ</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏆 <b>Daraja:</b> {user.rank}\n"
        f"💰 <b>Balans:</b> {user.balance} eko-ball\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Ism:</b> {user.fullname}\n"
        f"📞 <b>Tel:</b> {user.phone}\n"
        f"📍 <b>Hudud:</b> {user.get_region_display()}\n"
        f"🏫 <b>O'qish:</b> {user.education_place or '—'}\n\n"
        f"<i>Yashil Qo'llar bilan dunyoni birgalikda qutqaramiz!</i> 🌿"
    )

    if user.photo:
        try:
            with open(user.photo.path, 'rb') as photo:
                await message.answer_photo(photo=photo, caption=profile_text, parse_mode="HTML")
        except:
            await message.answer(profile_text, parse_mode="HTML")
    else:
        await message.answer(profile_text, parse_mode="HTML")

# 3. Регистрация хендлеров
def register_profile(dp: Dispatcher):
    # Главная кнопка профиля
    dp.register_message_handler(profile_menu, text="👤 Mening profilim", state="*")
    
    # Кнопка "Посмотреть"
    dp.register_message_handler(view_my_profile, text="📄 Profilni ko'rish", state="*")
    
    # Кнопка "Назад"
    dp.register_message_handler(
        lambda m: m.text == "⬅️ Orqaga", 
        lambda m: m.text == "⬅️ Orqaga", # Дополнительная проверка если нужно
        state="*"
    )