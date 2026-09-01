
import qrcode
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db import models
from tgbot.services.photo_cache import send_cached_photo

# ==========================================
# 1. QR CODE & ATTENDANCE LOGIC
# ==========================================

@sync_to_async
def process_qr_logic(scanner_tg_id, target_tg_id):
    """
    Processes the QR code scan.
    Permission is granted to any role EXCEPT regular volunteers.

    Returns: (result_text, volunteer, project)
    """
    from app_telegram.models import TGUser, ProjectParticipation, EcoProject

    scanner_user = TGUser.objects.filter(tg_id=scanner_tg_id).first()

    if not scanner_user or scanner_user.role == TGUser.Role.VOLUNTEER:
        return "❌ Sizda skanerlash huquqi yo'q! Bu imkoniyat faqat ishchi guruh uchun.", None, None

    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!", None, None

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
        project = EcoProject.objects.filter(is_active=True, region__in=search_regions).first()

    if not project:
        return f"❌ {volunteer.get_region_display()}da faol loyiha topilmadi!", None, None

    participation = ProjectParticipation.objects.filter(project=project, user=volunteer).first()
    if not participation:
        return f"❌ Volontyor '{project.title}' loyihasiga ro'yxatdan o'tmagan!", None, None

    if participation.status == 'attended':
        return f"⚠️ <b>{volunteer.fullname}</b> allaqachon tasdiqlangan!", volunteer, None

    participation.status = 'attended'
    participation.save()

    volunteer.refresh_from_db()

    success_text = (
        f"✅ <b>Tayyor!</b>\n"
        f"Foydalanuvchi: <b>{volunteer.fullname}</b> kelgani tasdiqlandi.\n"
        f"💰 <b>Yangi balans:</b> {volunteer.balance} ball\n"
        f"👤 <b>Skaner qildi:</b> {scanner_user.fullname} ({scanner_user.get_role_display()})"
    )
    return success_text, volunteer, project


async def show_qr_handler(message: types.Message):
    """Generates a personal QR code for the user"""
    bot_info = await message.bot.get_me()
    qr_link = f"https://t.me/{bot_info.username}?start=qr_{message.from_user.id}"

    def _generate_qr():
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_link)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        bio = BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio

    # QR-код одного и того же юзера всегда одинаковый (зависит только от
    # его tg_id и username бота) — кэшируем file_id, чтобы при повторных
    # заходах в раздел не генерировать картинку и не аплоадить её заново.
    await send_cached_photo(
        message, f"qr:{message.from_user.id}:{bot_info.username}", _generate_qr,
        caption="🌿 <b>Sizning shaxsiy eko-kodingiz!</b>\n\nTadbirga kelganingizda mas'ul xodimga ko'rsating."
    )

def register_qr_handlers(dp: Dispatcher):
    dp.register_message_handler(show_qr_handler, text="🌿 Mening QR-kodim", state="*")
