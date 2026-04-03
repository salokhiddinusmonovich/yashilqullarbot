from aiogram import types
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Dispatcher
from pathlib import Path
from asgiref.sync import sync_to_async
from app_telegram.models import Partner

BASE_DIR = Path(__file__).resolve().parents[2]

async def about_us(message: types.Message):
    # 1. Загружаем активных партнеров заранее
    partners = await sync_to_async(list)(Partner.objects.filter(is_active=True))

    # 2. Формируем текст "О нас"
    main_text = (
        "🌿 <b>Yashil Qo'llar</b> — barqaror kelajak harakati!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Bizning maqsadimiz — shahrimizni yashilroq qilish va "
        "ekologik madaniyatni yuksaltirish. Hozirda bizda <b>300+</b> "
        "faol ko'ngillilar bor! 💪\n\n"
    )

    # 3. Добавляем блок партнеров в это же сообщение
    kb = InlineKeyboardMarkup(row_width=2)
    
    if partners:
        main_text += "🤝 <b>Bizning hamkorlarimiz:</b>\n"
        for p in partners:
            main_text += f"🔹 {p.name}\n"
            # Добавляем кнопки в общую клавиатуру
            if p.telegram:
                kb.insert(InlineKeyboardButton(f"✈️ {p.name}", url=p.telegram))
            elif p.instagram: # Если нет ТГ, пробуем Инсту
                kb.insert(InlineKeyboardButton(f"📸 {p.name}", url=p.instagram))

    # Добавляем общую кнопку соцсетей самого проекта (опционально)
    kb.add(InlineKeyboardButton("🌐 Bizning saytimiz", url="https://yashilqollar.uz"))

    # 4. Отправляем ОДНИМ сообщением
    poster_path = BASE_DIR / "idk" / "poster.png"
    
    try:
        # Отправляем постер с общим текстом и всеми кнопками
        with open(poster_path, 'rb') as photo:
            await message.answer_photo(
                photo=photo,
                caption=main_text,
                reply_markup=kb,
                parse_mode="HTML"
            )
    except Exception as e:
        # Если фото не нашлось, шлем просто текст
        await message.answer(main_text, reply_markup=kb, parse_mode="HTML")

def register_about_us(dp: Dispatcher):
    dp.register_message_handler(
        about_us,
        lambda m: m.text == "🌟 Biz haqimizda",
        state="*"
    )