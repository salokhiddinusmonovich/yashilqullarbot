import qrcode
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from django.utils import timezone
# from app_telegram.models import TGUser, ProjectParticipation, EcoProject

# Список ID админов, которым разрешено сканировать
ADMIN_IDS = [7336334074, 998920105472, 998998951002, 998904815816, 998908291932]

@sync_to_async
def process_qr_logic(admin_id, target_tg_id):

    from app_telegram.models import TGUser, ProjectParticipation, EcoProject
    
    # 1. Проверка прав
    if admin_id not in ADMIN_IDS:
        return "❌ Sizda adminlik huquqi yo'q!", None

    # 2. Поиск волонтера
    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!", None

    # 3. Поиск активного проекта в регионе волонтера
    today = timezone.now().date()
    search_regions = [volunteer.region]
    if volunteer.region in ['tashkent_s', 'tashkent_v']:
        search_regions = ['tashkent_s', 'tashkent_v']

    project = EcoProject.objects.filter(
        is_active=True, 
        date__date=today, 
        region__in=search_regions
    ).first()

    if not project:
        # Если на сегодня нет, ищем любой активный в этом регионе
        project = EcoProject.objects.filter(is_active=True, region__in=search_regions).first()

    if not project:
        return f"❌ {volunteer.get_region_display()}da faol loyiha topilmadi!", None

    # 4. Проверка регистрации на этот проект
    participation = ProjectParticipation.objects.filter(project=project, user=volunteer).first()
    if not participation:
        return f"❌ Волонтер '{project.title}' лойиҳасига рўйхатдан ўтмаган!", None

    if participation.status == 'attended':
        return f"⚠️ <b>{volunteer.fullname}</b> аллақачон тасдиқланган!", volunteer

    # 5. Обновление статуса и сохранение
    participation.status = 'attended'
    participation.save() 
    
    # Обновляем объект, чтобы подтянулись баллы после save()
    volunteer.refresh_from_db()

    success_text = (
        f"✅ <b>Tayyor!</b>\n"
        f"Foydalanuvchi: <b>{volunteer.fullname}</b> kelgani tasdiqlandi.\n"
        f"💰 <b>Yangi balans:</b> {volunteer.balance} ball"
    )
    return success_text, volunteer

async def show_qr_handler(message: types.Message):
    """Генерация QR-кода для пользователя"""
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

def register_qr_handlers(dp: Dispatcher):
    dp.register_message_handler(show_qr_handler, text="🌿 Mening QR-kodim", state="*")