from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
from asgiref.sync import sync_to_async
from pathlib import Path
from app_telegram.models import TeamMemberYashilQullar, Partner

BASE_DIR = Path(__file__).resolve().parents[2]

# 1. Главная клавиатура раздела "О нас" (Внизу вместо основной)
ABOUT_REPLY_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Jamoamiz"), KeyboardButton(text="🤝 Hamkorlarimiz")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

# 2. Клавиатура выбора роли в команде
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
        "🌿 <b>Yashil Qo'llar</b> — barqaror kelajak harakati!\n\n"
        "Bizning maqsadimiz — shahrimizni yashilroq qilish va ekologik "
        "madaniyatni yuksaltirish.\n\n"
        "Quyidagilardan birini tanlang: 👇"
    )
    
    poster_path = BASE_DIR / "idk" / "poster.png"
    
    # Отправляем постер и МЕНЯЕМ кнопки внизу телефона
    try:
        with open(poster_path, 'rb') as photo:
            await message.answer_photo(
                photo=photo,
                caption=main_text,
                reply_markup=ABOUT_REPLY_KB, # Кнопки появятся внизу
                parse_mode="HTML"
            )
    except Exception:
        await message.answer(main_text, reply_markup=ABOUT_REPLY_KB, parse_mode="HTML")

async def show_team_selection(message: types.Message):
    await message.answer(
        "Jamoamiz yo'nalishini tanlang: 👇",
        reply_markup=TEAM_MENU_KB
    )

async def show_partners_list(message: types.Message):
    partners = await sync_to_async(lambda: list(Partner.objects.filter(is_active=True)))()
    
    if not partners:
        await message.answer("Hozircha hamkorlar ro'yxati bo'sh.")
        return

    for p in partners:
        caption = f"<b>{p.name}</b>\n\n{p.description if p.description else ''}"
        # Здесь можно оставить инлайн кнопки для ссылок, они не мешают кнопкам внизу
        if p.logo:
            try:
                await message.answer_photo(InputFile(p.logo.path), caption=caption, parse_mode="HTML")
            except Exception:
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

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
        # Убираем эмодзи из кнопки (🌟, 💻 и т.д.), чтобы оставить только текст роли
        role_name = message.text.split(maxsplit=1)[-1] 
        
        # ФОРМАТИРОВАНИЕ:
        # 👤 — человечек перед именем
        # • — кружочек перед навыками
        caption = f"👤 <b>{member.fullname}</b>\n"
        caption += f"{message.text}\n\n" # Оставляем роль со стикером как на кнопке
        
        if member.skills:
            # Добавляем маленький кружочек перед каждой строкой навыков
            caption += f"• {member.skills}\n\n"

        if member.telegram_username:
            username = member.telegram_username.replace('@', '')
            caption += f"Telegram: @{username}"

        # Отправка фото
        if member.photo:
            try:
                await message.answer_photo(
                    photo=InputFile(member.photo.path),
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Ошибка фото: {e}")
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

# --- РЕГИСТРАЦИЯ ---
def register_about_and_team(dp: Dispatcher):
    # Главная кнопка "О нас"
    dp.register_message_handler(about_us, text="🌟 Biz haqimizda", state="*")
    
    # Кнопки под телефоном (Reply)
    dp.register_message_handler(show_team_selection, text="👥 Jamoamiz", state="*")
    dp.register_message_handler(show_partners_list, text="🤝 Hamkorlarimiz", state="*")
    
    # Кнопки выбора роли
    dp.register_message_handler(
        show_team_members_by_focus, 
        lambda m: m.text in ["🌟 Project Lead", "💻 Digital Lead", "📸 Media Lead", "📋 Organization"],
        state="*"
    )