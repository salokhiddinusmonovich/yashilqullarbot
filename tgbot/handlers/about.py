from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from pathlib import Path
from app_telegram.models import Partner

BASE_DIR = Path(__file__).resolve().parents[2]


ABOUT_REPLY_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🤝 Hamkorlarimiz")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)

async def about_us(message: types.Message):
    main_text = (
        "🌿 <b>Yashil Qo'llar</b> — barqaror kelajak sari!\n\n"
        "Maqsadimiz — yoshlar orasida ekologik madaniyatni rivojnatirish.  "
        "Safimizda <b>1400+</b> faol ko'ngillilar bor! 💪\n\n"
    )
    poster_path = BASE_DIR / "idk" / "poster.png"
    try:
        with open(poster_path, 'rb') as photo:
            await message.answer_photo(photo=photo, caption=main_text, reply_markup=ABOUT_REPLY_KB, parse_mode="HTML")
    except Exception:
        await message.answer(main_text, reply_markup=ABOUT_REPLY_KB, parse_mode="HTML")

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

# --- РЕГИСТРАЦИЯ ---
def register_about_and_team(dp: Dispatcher):
    dp.register_message_handler(about_us, text="🌟 Biz haqimizda", state="*")
    dp.register_message_handler(show_partners_list, text="🤝 Hamkorlarimiz", state="*")