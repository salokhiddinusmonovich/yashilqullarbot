from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from app_telegram.models import TeamMemberYashilQullar

TEAM_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌟 Project Lead"), KeyboardButton(text="💻 Digital Lead")],
        [KeyboardButton(text="📸 Media Lead"), KeyboardButton(text="📋 Organization")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

async def show_team_categories(message: types.Message):
    await message.answer(
        "Yashil Qo‘llar jamoasining yo‘nalishini tanlang: 👇",
        reply_markup=TEAM_MENU_KB
    )

async def show_team_members_by_focus(message: types.Message):
    focus_map = {
        "🌟 Project Lead": "founder",
        "💻 Digital Lead": "digital",
        "📸 Media Lead": "media",
        "📋 Organization": "organization"
    }
    
    selected_focus = focus_map.get(message.text)
    
    # Подгружаем tg_user сразу, чтобы не делать лишних запросов в цикле
    members = await sync_to_async(lambda: list(
        TeamMemberYashilQullar.objects.filter(focus__iexact=selected_focus).select_related('tg_user')
    ))()

    if not members:
        await message.answer("Hozircha bu bo‘limda a’zolar mavjud emas.")
        return

    for member in members:
        user = member.tg_user
        
        # Основная информация
        caption = (
            f"👤 <b>{user.fullname}</b>\n"
            f"• Yosh: {user.age or '—'}\n"
        )
        
        # Добавляем навыки (skills), если они заполнены
        if member.skills:
            caption += f"{member.skills}\n"

        # Контакты
        contact = member.telegram_username or user.tg_id
        contact_str = str(contact).replace('@', '')
        caption += f"• 🔗 @{contact_str}\n"

        # Отправка фото или просто текста
        if user.photo:
            try:
                # В aiogram 2.x лучше передавать открытый файл или путь
                photo_file = types.InputFile(user.photo.path)
                await message.answer_photo(
                    photo=photo_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception:
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

def register_team(dp: Dispatcher):
    dp.register_message_handler(show_team_categories, text="🎯 Loyiha yetakchilari", state="*")
    
    dp.register_message_handler(
        show_team_members_by_focus, 
        lambda m: m.text in ["🌟 Project Lead", "💻 Digital Lead", "📸 Media Lead", "📋 Organization"],
        state="*"
    )