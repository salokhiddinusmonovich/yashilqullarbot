"""
Короткая инструкция "как пользоваться ботом" — для волонтёров и
отдельно для координаторов (всех ролей кроме volunteer).
Показывается после регистрации/привязки и по кнопке "❓ Qo'llanma" / /help.
"""
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async

from ..keyboards.reply import guide_text

VOLUNTEER_GUIDE = (
    "📖 <b>Botdan qanday foydalaniladi?</b>\n\n"
    "Tadbirda qatnashish va sertifikat olish uchun 3 qadam:\n\n"
    "1️⃣ <b>🌱 Tadbirlar → 📅 Kelgusi tadbirlar</b> — tadbirni tanlang va "
    "<b>«✅ Ro'yxatdan o'tish»</b> tugmasini bosing.\n"
    "❗ Botda ro'yxatdan o'tish — bu tadbirga yozilish degani EMAS. "
    "Har bir tadbirga alohida yozilish kerak!\n\n"
    "2️⃣ Tadbir kuni <b>🌿 Mening QR-kodim</b> ni oching va koordinatorga ko'rsating.\n\n"
    "3️⃣ Koordinator skaner qilgach, sizga <b>+10 ball</b> tushadi va siz "
    "sertifikat ro'yxatiga kirasiz. ✅\n\n"
    "👤 <b>Mening profilim</b> — ism, rasm, hududni o'zgartirish, balans.\n"
    "📍 Tadbirlar hududingiz bo'yicha ko'rsatiladi — hududingiz to'g'ri ekanini tekshiring."
)

COORDINATOR_GUIDE = (
    "\n\n🧑‍💼 <b>Koordinatorlar uchun:</b>\n"
    "• Volontyorning QR-kodini telefon kamerasi bilan skaner qiling — havola botni "
    "ochadi va kelgani avtomatik tasdiqlanadi.\n"
    "• Agar volontyor tadbirga yozilmagan bo'lsa — bot uni <b>o'zi qo'shadi</b> "
    "va kelgan deb belgilaydi. Saytga kirish shart emas.\n"
    "• Qatnashchilar ro'yxati va Excel — /admin (faqat adminlar uchun)."
)


@sync_to_async
def _is_staff(tg_id: int) -> bool:
    from app_telegram.models import TGUser
    user = TGUser.objects.filter(tg_id=tg_id).only("role", "is_admin").first()
    return bool(user and (user.is_admin or user.role != TGUser.Role.VOLUNTEER))


async def send_guide(message: types.Message, tg_id: int = None):
    text = VOLUNTEER_GUIDE
    if await _is_staff(tg_id or message.chat.id):
        text += COORDINATOR_GUIDE
    await message.answer(text, parse_mode="HTML")


async def help_handler(message: types.Message):
    await send_guide(message, message.from_user.id)


def register_help(dp: Dispatcher):
    dp.register_message_handler(help_handler, commands=["help"], state="*")
    dp.register_message_handler(help_handler, text=guide_text, state="*")
