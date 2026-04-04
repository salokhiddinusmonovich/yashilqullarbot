from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from pathlib import Path
from app_telegram.models import TeamMemberYashilQullar, Partner

BASE_DIR = Path(__file__).resolve().parents[2]

# 1. ОБНОВЛЕННАЯ ГЛАВНАЯ КЛАВИАТУРА
ABOUT_REPLY_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎯 Loyiha yetakchilari"), KeyboardButton(text="🤝 Hamkorlarimiz")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

# 2. КЛАВИАТУРА ВЫБОРА РОЛИ (без изменений)
TEAM_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌟 Project Lead"), KeyboardButton(text="💻 Digital Lead")],
        [KeyboardButton(text="📸 Media Lead"), KeyboardButton(text="📋 Organization")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

# --- ХЕНДЛЕРЫ ---

async def about_us(message: types.Message):
    main_text = (
        "🌿 <b>Yashil Qo'llar</b> — barqaror kelajak sari!\n\n"
        "Maqsadimiz — yoshlar orasida ekologik madaniyatni rivojnatirish.  "
        "Safimizda 300+ faol ko'ngillilar bor! 💪\n\n"
    )
    poster_path = BASE_DIR / "idk" / "poster.png"
    try:
        with open(poster_path, 'rb') as photo:
            await message.answer_photo(photo=photo, caption=main_text, reply_markup=ABOUT_REPLY_KB, parse_mode="HTML")
    except Exception:
        await message.answer(main_text, reply_markup=ABOUT_REPLY_KB, parse_mode="HTML")

# Функция теперь реагирует на "🎯 Loyiha yetakchilari"
async def show_team_selection(message: types.Message):
    await message.answer("Loyiha yetakchilari yo'nalishini tanlang: 👇", reply_markup=TEAM_MENU_KB)

async def show_partners_list(message: types.Message):
    partners = await sync_to_async(lambda: list(Partner.objects.filter(is_active=True)))()
    if not partners:
        await message.answer("Hozircha hamkorlar ro'yxati bo'sh.")
        return

    await message.answer("🤝 <b>Hamkorlarimiz: </b>", parse_mode="HTML")
    for p in partners:
        caption = f"<b>{p.name}</b>\n"
        if p.description: caption += f"\n{p.description}\n"

        kb = InlineKeyboardMarkup(row_width=2)
        buttons = []
        if p.telegram: buttons.append(InlineKeyboardButton("Telegram", url=p.telegram))
        if p.instagram: buttons.append(InlineKeyboardButton("Instagram", url=p.instagram))
        if p.linkedin: buttons.append(InlineKeyboardButton("LinkedIn", url=p.linkedin))
        
        if buttons: kb.add(*buttons)

        if p.logo:
            try:
                await message.answer_photo(photo=InputFile(p.logo.path), caption=caption, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await message.answer(caption, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=kb, parse_mode="HTML")

async def show_team_members_by_focus(message: types.Message):
    focus_map = {
        "🌟 Project Lead": "founder",
        "💻 Digital Lead": "digital",
        "📸 Media Lead": "media",
        "📋 Organization": "organization"
    }
    selected_focus = focus_map.get(message.text)
    if not selected_focus: return

    members = await sync_to_async(lambda: list(TeamMemberYashilQullar.objects.filter(focus=selected_focus)))()
    if not members:
        await message.answer("Hozircha bu bo‘limda a’zolar mavjud emas.")
        return

    for member in members:
        caption = f"👤 <b>{member.fullname}</b>\n"
        if member.skills: caption += f"{member.skills}\n"
        if member.telegram_username:
            username = member.telegram_username.replace('@', '')
            link = username if "t.me" in username else f"@{username}"
            caption += f"Telegram: {link}"

        if member.photo:
            try:
                await message.answer_photo(photo=InputFile(member.photo.path), caption=caption, parse_mode="HTML")
            except Exception:
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

# --- РЕГИСТРАЦИЯ (ИСПРАВЛЕНО ПОД НОВУЮ КНОПКУ) ---
def register_about_and_team(dp: Dispatcher):
    dp.register_message_handler(about_us, text="🌟 Biz haqimizda", state="*")
    
    # Теперь реагируем на новый текст кнопки
    dp.register_message_handler(show_team_selection, text="🎯 Loyiha yetakchilari", state="*")
    
    dp.register_message_handler(show_partners_list, text="🤝 Hamkorlarimiz", state="*")
    dp.register_message_handler(
        show_team_members_by_focus, 
        lambda m: m.text in ["🌟 Project Lead", "💻 Digital Lead", "📸 Media Lead", "📋 Organization"],
        state="*"
    )