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

async def send_user_qr(message: types.Message):
    # Логика генерации (мы ее писали выше)
    bot_info = await message.bot.get_me()
    qr_link = f"https://t.me/{bot_info.username}?start=qr_{message.from_user.id}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_link)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    # В aiogram 2.x отправляем так:
    await message.answer_photo(
        photo=bio,
        caption="🌿 <b>Sizning shaxsiy eko-kodingiz!</b>\n\nTadbirga kelganingizda adminga ko'rsating."
    )

@sync_to_async
def process_qr_logic(admin_id, target_tg_id):
    # 1. Проверка на админа
    if admin_id not in ADMIN_IDS:
        return "❌ Sizda adminlik huquqi yo'q!"

    # 2. Поиск волонтера
    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!"

    # 3. Поиск активного проекта сегодня в регионе юзера
    today = timezone.now().date()
    project = EcoProject.objects.filter(
        is_active=True, 
        date=today, 
        region=volunteer.region
    ).first()

    if not project:
        return f"❌ {volunteer.get_region_display()}da bugun faol loyiha topilmadi!"

    # 4. Проверка регистрации
    participation = ProjectParticipation.objects.filter(
        project=project, 
        user=volunteer
    ).first()

    if not participation:
        return "❌ Bu foydalanuvchi ushbu loyihaga ro'yxatdan o'tmagan!"

    if participation.status == 'attended':
        return f"⚠️ {volunteer.fullname} allaqachon tasdiqlangan!"

    # 5. Успех
    participation.status = 'attended'
    participation.save()
    
    return f"✅ <b>Tayyor!</b>\n{volunteer.fullname} kelgani tasdiqlandi.\nLoyixa: {project.title}"



def register_qr_handlers(dp: Dispatcher):
    """Регистрируем QR хендлеры отдельно"""
    # 1. Хендлер для команды старт с аргументом qr_
    dp.register_message_handler(
        send_user_qr, 
        lambda m: m.get_args().startswith('qr_'), 
        commands=["start"], 
        state="*"
    )
    
    # 2. Хендлер для кнопки в меню
    dp.register_message_handler(
        process_qr_logic, 
        text="🌿 Mening QR-kodim", 
        state="*"
    )