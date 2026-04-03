from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
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

async def show_partners_list(callback: types.CallbackQuery):
    # Загружаем только активных партнеров
    partners = await sync_to_async(lambda: list(Partner.objects.filter(is_active=True)))()
    
    if not partners:
        await callback.message.answer("Hozircha hamkorlar ro'yxati bo'sh.")
        await callback.answer()
        return

    # Сообщение-заголовок
    await callback.message.answer("🤝 <b>Bizning hamkorlarimiz:</b>", parse_mode="HTML")

    for p in partners:
        # Текст карточки партнера
        caption = f"<b>{p.name}</b>\n"
        if p.description:
            caption += f"\n{p.description}\n"

        # СОЗДАЕМ КНОПКИ (Inline)
        kb = InlineKeyboardMarkup(row_width=2)
        buttons = []
        
        if p.telegram:
            buttons.append(InlineKeyboardButton("Telegram", url=p.telegram))
        if p.instagram:
            buttons.append(InlineKeyboardButton("Instagram", url=p.instagram))
        if p.linkedin:
            buttons.append(InlineKeyboardButton("LinkedIn", url=p.linkedin))
        if p.website:
            buttons.append(InlineKeyboardButton("Website", url=p.website))
            
        if buttons:
            kb.add(*buttons)

        # Отправка логотипа с кнопками
        if p.logo:
            try:
                await callback.message.answer_photo(
                    photo=InputFile(p.logo.path),
                    caption=caption,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Partner photo error: {e}")
                await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")
        else:
            # Если логотипа нет, просто текст с кнопками
            await callback.message.answer(caption, reply_markup=kb, parse_mode="HTML")
    
    await callback.answer()

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
        # 1. Имя жирным с человечком
        caption = f"👤 <b>{member.fullname}</b>\n"
        
        # 2. Текст из Skills выводим КАК ЕСТЬ (со всеми твоими точками и переносами)
        if member.skills:
            # Просто добавляем текст из базы, не удаляя никакие символы
            caption += f"{member.skills}\n"

        # 3. Контакт в Telegram (с новой строки)
        if member.telegram_username:
            username = member.telegram_username.replace('@', '')
            # Если это ссылка t.me, оставляем как есть, если юзернейм — добавляем @
            if "t.me" in username:
                caption += f"Telegram: {username}"
            else:
                caption += f"Telegram: @{username}"

        # Отправка фото
        if member.photo:
            try:
                await message.answer_photo(
                    photo=InputFile(member.photo.path),
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception:
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

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