import qrcode
from io import BytesIO
from aiogram import types
from asgiref.sync import sync_to_async
from django.utils import timezone
from aiogram import Dispatcher
# ВАЖНО: импортируй свои модели правильно
from app_telegram.models import TGUser, ProjectParticipation, EcoProject 

# ТВОЙ ТЕЛЕГРАМ ID (и твоих помощников)
ADMIN_IDS = [7336334074, 998920105472, 998998951002, 998904815816, 998908291932] # Замени на свои цифры!

# --- ЛОГИКА (МЯСО) ---

async def send_user_qr(message: types.Message):
    """Генерирует и отправляет QR код юзеру"""
    bot_info = await message.bot.get_me()
    qr_link = f"https://t.me/{bot_info.username}?start=qr_{message.from_user.id}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_link)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    await message.answer_photo(
        photo=bio,
        caption="🌿 <b>Sizning shaxsiy eko-kodingiz!</b>\n\nTadbirga kelganingizda adminga ko'rsating."
    )

@sync_to_async
def process_qr_logic(admin_id, target_tg_id):
    """Проверяет данные в базе (Django)"""
    if admin_id not in ADMIN_IDS:
        return "❌ Sizda adminlik huquqi yo'q!"

    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!"

    today = timezone.now().date()
    project = EcoProject.objects.filter(is_active=True, date=today, region=volunteer.region).first()

    if not project:
        return f"❌ {volunteer.get_region_display()}da bugun faol loyiha topilmadi!"

    participation = ProjectParticipation.objects.filter(project=project, user=volunteer).first()
    if not participation:
        return "❌ Bu foydalanuvchi ushbu loyihaga ro'yxatdan o'tmagan!"

    if participation.status == 'attended':
        return f"⚠️ {volunteer.fullname} allaqachon tasdiqlangan!"

    participation.status = 'attended'
    participation.save()
    return f"✅ <b>Tayyor!</b>\n{volunteer.fullname} kelgani tasdiqlandi."

# --- ХЕНДЛЕРЫ (РУКИ) ---

async def show_qr_handler(message: types.Message):
    await send_user_qr(message)

async def scan_qr_handler(message: types.Message):
    args = message.get_args()
    target_id = args.replace('qr_', '')
    result = await process_qr_logic(message.from_user.id, target_id)
    await message.answer(result, parse_mode="HTML")
    
    if "✅" in result:
        try:
            await message.bot.send_message(target_id, "🌟 <b>Tasdiqlandi!</b>\nBallar hisobingizga qo'shildi! 🌿", parse_mode="HTML")
        except: pass

def register_qr_handlers(dp: Dispatcher):
    # Важно: этот хендлер должен быть выше обычного старта!
    dp.register_message_handler(scan_qr_handler, lambda m: m.get_args() and m.get_args().startswith('qr_'), commands=["start"], state="*")
    dp.register_message_handler(show_qr_handler, text="🌿 Mening QR-kodim", state="*")