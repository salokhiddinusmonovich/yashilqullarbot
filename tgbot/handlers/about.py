from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from pathlib import Path
from app_telegram.models import TeamMemberYashilQullar, Partner

BASE_DIR = Path(__file__).resolve().parents[2]

# --- КЛАВИАТУРЫ ---

# Клавиатура выбора категории команды (Обычные кнопки)
TEAM_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌟 Project Lead"), KeyboardButton(text="💻 Digital Lead")],
        [KeyboardButton(text="📸 Media Lead"), KeyboardButton(text="📋 Organization")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

# Инлайн-кнопки для раздела "About"
ABOUT_INLINE_KB = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("👥 Jamoamiz", callback_data="show_team_menu"),
    InlineKeyboardButton("🤝 Hamkorlarimiz", callback_data="show_partners")
)

# --- ХЕНДЛЕРЫ ---

# 1. Главное меню "О нас"
async def about_us(message: types.Message):
    main_text = (
        "🌿 <b>Yashil Qo'llar</b> — barqaror kelajak harakati!\n\n"
        "Bizning maqsadimiz — shahrimizni yashilroq qilish va ekologik "
        "madaniyatni yuksaltirish. Hozirda bizda <b>300+</b> faol ko'ngillilar bor! 💪\n\n"
        "Quyidagilardan birini tanlang: 👇"
    )
    
    poster_path = BASE_DIR / "idk" / "poster.png"
    
    try:
        with open(poster_path, 'rb') as photo:
            await message.answer_photo(
                photo=photo,
                caption=main_text,
                reply_markup=ABOUT_INLINE_KB,
                parse_mode="HTML"
            )
    except Exception:
        await message.answer(main_text, reply_markup=ABOUT_INLINE_KB, parse_mode="HTML")

# 2. Переход к меню команды (через Callback)
async def call_show_team_menu(callback: types.CallbackQuery):
    await callback.message.answer(
        "Yashil Qo‘llar jamoasining yo‘nalishini tanlang: 👇",
        reply_markup=TEAM_MENU_KB
    )
    await callback.answer()

# 3. Вывод ПАРТНЕРОВ с фото
async def call_show_partners(callback: types.CallbackQuery):
    partners = await sync_to_async(lambda: list(Partner.objects.filter(is_active=True)))()
    
    if not partners:
        await callback.message.answer("Hozircha hamkorlar ro'yxati bo'sh.")
        await callback.answer()
        return

    await callback.message.answer("<b>Bizning hamkorlarimiz:</b>", parse_mode="HTML")

    for p in partners:
        caption = f"<b>{p.name}</b>\n\n{p.description if p.description else ''}"
        
        kb = InlineKeyboardMarkup()
        if p.telegram: kb.add(InlineKeyboardButton("Telegram", url=p.telegram))
        if p.instagram: kb.add(InlineKeyboardButton("Instagram", url=p.instagram))

        if p.logo:
            try:
                await callback.message.answer_photo(
                    photo=InputFile(p.logo.path),
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception:
                await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")
    
    await callback.answer()

# 4. Вывод ЧЛЕНОВ КОМАНДЫ (твоя логика без VIP и стикеров)
async def show_team_members_by_focus(message: types.Message):
    focus_map = {
        "🌟 Project Lead": "founder",
        "💻 Digital Lead": "digital",
        "📸 Media Lead": "media",
        "📋 Organization": "organization"
    }
    
    selected_focus = focus_map.get(message.text)
    if not selected_focus: return

    members = await sync_to_async(lambda: list(
        TeamMemberYashilQullar.objects.filter(focus=selected_focus)
    ))()

    if not members:
        await message.answer("Hozircha bu bo‘limda a’zolar mavjud emas.")
        return

    for member in members:
        role_name = message.text.split(maxsplit=1)[-1] 
        caption = f"<b>{member.fullname}</b>\n{role_name}\n\n"
        if member.skills: caption += f"{member.skills}\n\n"
        if member.telegram_username:
            caption += f"Telegram: @{member.telegram_username.replace('@', '')}"

        if member.photo:
            try:
                await message.answer_photo(photo=InputFile(member.photo.path), caption=caption, parse_mode="HTML")
            except Exception:
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

# --- РЕГИСТРАЦИЯ ---
def register_about_and_team(dp: Dispatcher):
    # Главная кнопка
    dp.register_message_handler(about_us, lambda m: m.text == "🌟 Biz haqimizda", state="*")
    
    # Callback-кнопки под постером
    dp.register_callback_query_handler(call_show_team_menu, text="show_team_menu", state="*")
    dp.register_callback_query_handler(call_show_partners, text="show_partners", state="*")
    
    # Кнопки категорий команды
    dp.register_message_handler(
        show_team_members_by_focus, 
        lambda m: m.text in ["🌟 Project Lead", "💻 Digital Lead", "📸 Media Lead", "📋 Organization"],
        state="*"
    )