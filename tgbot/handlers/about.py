from aiogram import types
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Dispatcher
from pathlib import Path
from asgiref.sync import sync_to_async
from app_telegram.models import Partner # Импортируем нашу новую модель

BASE_DIR = Path(__file__).resolve().parents[2]

async def about_us(message: types.Message):
    # 1. Основное фото и текст о проекте
    poster_path = BASE_DIR / "idk" / "poster.png"
    main_text = (
        "🌱 <b>Yashil Qo'llar</b> — bu barqaror kelajak uchun harakat.\n\n"
        "Bizning maqsadimiz — shahrimizni yashilroq qilish va "
        "ekologik madaniyatni yuksaltirish."
    )

    try:
        await message.answer_photo(
            photo=InputFile(poster_path),
            caption=main_text,
            parse_mode="HTML"
        )
    except Exception:
        await message.answer(main_text, parse_mode="HTML")

    # 2. Вывод спонсоров
    partners = await sync_to_async(list)(Partner.objects.filter(is_active=True))

    if partners:
        await message.answer("🤝 <b>Bizning hamkorlarimiz:</b>", parse_mode="HTML")
        
        for partner in partners:
            # Формируем текст
            partner_text = f"🔹 <b>{partner.name}</b>"
            if partner.description:
                partner_text += f"\n<i>{partner.description}</i>"

            # Создаем кнопки соцсетей (только если они заполнены)
            kb = InlineKeyboardMarkup(row_width=2)
            buttons = []
            if partner.instagram:
                buttons.append(InlineKeyboardButton("Instagram", url=partner.instagram))
            if partner.telegram:
                buttons.append(InlineKeyboardButton("Telegram", url=partner.telegram))
            if partner.linkedin:
                buttons.append(InlineKeyboardButton("LinkedIn", url=partner.linkedin))
            
            kb.add(*buttons)

            # Если есть логотип — шлем фото, если нет — только текст
            if partner.logo:
                try:
                    with open(partner.logo.path, 'rb') as photo:
                        await message.answer_photo(photo=photo, caption=partner_text, reply_markup=kb, parse_mode="HTML")
                except:
                    await message.answer(partner_text, reply_markup=kb, parse_mode="HTML")
            else:
                await message.answer(partner_text, reply_markup=kb, parse_mode="HTML")

def register_about_us(dp: Dispatcher):
    dp.register_message_handler(
        about_us,
        lambda m: m.text == "🌟 Biz haqimizda",
        state="*"
    )