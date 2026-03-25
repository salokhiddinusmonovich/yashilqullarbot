from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from app_telegram.models import Partner

async def show_partners(message: types.Message):
    # Hamma hamkorlarni bazadan olamiz
    partners = await sync_to_async(list)(Partner.objects.all())

    if not partners:
        await message.answer("ℹ️ Hozircha hamkorlar ro'yxati bo'sh.")
        return

    for partner in partners:
        caption_text = f"🤝 <b>{partner.name}</b>\n"
        if partner.description:
            caption_text += f"\n{partner.description}"

        # Tugmalar klaviaturasi
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        buttons = []

        # LOGIKA: Faqat link mavjud bo'lsa tugmani qo'shamiz
        if partner.website:
            buttons.append(types.InlineKeyboardButton("🌐 Veb-sayt", url=partner.website))
        
        if partner.telegram:
            buttons.append(types.InlineKeyboardButton("✈️ Telegram", url=partner.telegram))
            
        if partner.instagram:
            buttons.append(types.InlineKeyboardButton("📸 Instagram", url=partner.instagram))

        # Agar bitta bo'lsa ham tugma bo'lsa, klaviaturaga qo'shamiz
        if buttons:
            keyboard.add(*buttons)
        else:
            keyboard = None # Tugma yo'q bo'lsa, klaviaturani yubormaymiz

        # Rasm bilan yoki rasmsiz yuborish
        if partner.logo:
            try:
                # Docker ichida media fayllar yo'lini to'g'ri ko'rsatish
                with open(partner.logo.path, 'rb') as photo:
                    await message.answer_photo(
                        photo=photo,
                        caption=caption_text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
            except Exception:
                # Agar rasm topilmasa, shunchaki matn yuboramiz
                await message.answer(caption_text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(caption_text, reply_markup=keyboard, parse_mode="HTML")

def register_partners(dp: Dispatcher):
    dp.register_message_handler(
        show_partners, 
        lambda m: "Hamkorlarimiz" in m.text, 
        state="*"
    )