from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from pathlib import Path
from app_telegram.models import Partner
from tgbot.i18n import t, variants
from tgbot.services.photo_cache import send_cached_photo, file_cache_key

BASE_DIR = Path(__file__).resolve().parents[2]


def about_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_partners"))],
            [KeyboardButton(text=t("btn_back"))],
        ],
        resize_keyboard=True,
    )

async def about_us(message: types.Message):
    main_text = t("about_text")
    poster_path = BASE_DIR / "tgbot" / "assets" / "poster.png"
    try:
        # Постер один и тот же для всех — после первой отправки Telegram
        # уже хранит его у себя, дальше просто переиспользуем file_id
        # вместо повторной загрузки файла с диска на каждый /about.
        await send_cached_photo(
            message, file_cache_key(poster_path), lambda: open(poster_path, 'rb'),
            caption=main_text, reply_markup=about_kb(), parse_mode="HTML"
        )
    except Exception:
        await message.answer(main_text, reply_markup=about_kb(), parse_mode="HTML")

async def show_partners_list(message: types.Message):
    partners = await sync_to_async(lambda: list(Partner.objects.filter(is_active=True)))()
    if not partners:
        await message.answer(t("partners_empty"))
        return

    await message.answer(t("partners_title"))
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
                await send_cached_photo(
                    message, file_cache_key(p.logo.path), lambda path=p.logo.path: open(path, 'rb'),
                    caption=caption, reply_markup=kb, parse_mode="HTML"
                )
            except Exception:
                await message.answer(caption, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(caption, reply_markup=kb, parse_mode="HTML")

# --- РЕГИСТРАЦИЯ ---
def register_about_and_team(dp: Dispatcher):
    dp.register_message_handler(about_us, text=variants("btn_about"), state="*")
    dp.register_message_handler(show_partners_list, text=variants("btn_partners"), state="*")