from aiogram import types
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Dispatcher
from pathlib import Path
from asgiref.sync import sync_to_async
from app_telegram.models import Partner

BASE_DIR = Path(__file__).resolve().parents[2]

async def about_us(message: types.Message):
    # 1. Загружаем активных партнеров
    partners = await sync_to_async(list)(Partner.objects.filter(is_active=True))

    # 2. Базовый текст (Всегда есть)
    main_text = (
        "🌿 <b>Yashil Qo'llar</b> — barqaror kelajak harakati!\n"
        
        "Bizning maqsadimiz — shahrimizni yashilroq qilish va "
        "ekologik madaniyatni yuksaltirish. Hozirda bizda <b>300+</b> "
        "faol ko'ngillilar bor! 💪"
    )

    kb = InlineKeyboardMarkup(row_width=2)

    # 3. Условие: Добавляем блок партнеров только если они СУЩЕСТВУЮТ
    if partners:
        main_text += "\n\n🤝 <b>Bizning hamkorlarimiz:</b>\n"
        for p in partners:
            main_text += f"🔹 {p.name}\n"
            # Добавляем кнопку ссылки партнера (Telegram приоритетнее Instagram)
            link = p.telegram or p.instagram or p.linkedin
            if link:
                kb.insert(InlineKeyboardButton(f"🔗 {p.name}", url=link))
        
        # Добавляем разделитель в клавиатуру, если есть партнеры
        kb.add(InlineKeyboardButton("🌐 Loyiha sayti", url="https://yashilqollar.uz"))
    else:
        # Если партнеров нет — просто одна кнопка сайта (или вообще без кнопок)
        kb.add(InlineKeyboardButton("🌐 Batafsil ma'lumot", url="https://yashilqollar.uz"))

    # 4. Отправка
    poster_path = BASE_DIR / "idk" / "poster.png"
    
    try:
        with open(poster_path, 'rb') as photo:
            await message.answer_photo(
                photo=photo,
                caption=main_text,
                reply_markup=kb,
                parse_mode="HTML"
            )
    except Exception:
        # Если файла нет — шлем просто текст
        await message.answer(main_text, reply_markup=kb, parse_mode="HTML")

def register_about_us(dp: Dispatcher):
    dp.register_message_handler(
        about_us,
        lambda m: m.text == "🌟 Biz haqimizda",
        state="*"
    )