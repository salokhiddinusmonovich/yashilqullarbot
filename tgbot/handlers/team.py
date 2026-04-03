from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile
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
    
    # Теперь мы не ищем tg_user, а берем данные прямо из TeamMemberYashilQullar
    members = await sync_to_async(lambda: list(
        TeamMemberYashilQullar.objects.filter(focus=selected_focus)
    ))()

    if not members:
        await message.answer("Hozircha bu bo‘limda a’zolar mavjud emas.")
        return

    for member in members:
        # ТЕПЕРЬ ДАННЫЕ БЕРЕМ НАПРЯМУЮ ИЗ member
        caption = (
            f"👤 <b>{member.fullname}</b>\n"
            f"• Rol: {message.text}\n"
        )
        
        if member.skills:
            caption += f"• Ko'nikmalar: {member.skills}\n"

        if member.telegram_username:
            username = member.telegram_username.replace('@', '')
            caption += f"• Telegram: @{username}\n"

        # Отправка фото
        if member.photo:
            try:
                # Берем путь к фото прямо из поля member.photo
                photo_file = InputFile(member.photo.path)
                await message.answer_photo(
                    photo=photo_file,
                    caption=caption,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Error sending photo: {e}")
                await message.answer(caption, parse_mode="HTML")
        else:
            await message.answer(caption, parse_mode="HTML")

def register_team(dp: Dispatcher):
    # ПРОВЕРЬ ЭТОТ ТЕКСТ! Он должен быть таким же, как в главном меню
    dp.register_message_handler(show_team_categories, text="🎯 Loyiha yetakchilari", state="*")
    
    dp.register_message_handler(
        show_team_members_by_focus, 
        lambda m: m.text in ["🌟 Project Lead", "💻 Digital Lead", "📸 Media Lead", "📋 Organization"],
        state="*"
    )