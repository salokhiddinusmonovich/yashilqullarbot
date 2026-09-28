
import qrcode
from html import escape
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from tgbot.i18n import t, variants, region_label, role_label
from tgbot.services.photo_cache import send_cached_photo

# ==========================================
# 1. QR CODE & ATTENDANCE LOGIC
# ==========================================

@sync_to_async
def process_qr_logic(scanner_tg_id, target_tg_id):
    """
    Скан QR из бота (ссылка t.me/<bot>?start=qr_<id>). Логика общая с
    Mini App — app_telegram/services.py; здесь только тексты.
    Не записан на мероприятие — записывается автоматически.

    Returns: (result_text, volunteer, project, confirmed)
      confirmed=True — посещение только что засчитано (надо уведомить волонтёра).
    """
    from app_telegram.models import TGUser
    from app_telegram import services

    scanner_user = TGUser.objects.filter(tg_id=scanner_tg_id).first()
    if not services.is_staff(scanner_user):
        return t("qr_no_rights"), None, None, False

    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return t("qr_user_not_found"), None, None, False

    project = services.pick_project(volunteer, scanner_user)
    if not project:
        # регион, в котором искали: свой — для координатора, волонтёра — для основателя
        region = scanner_user.region if services.scan_regions(scanner_user) else volunteer.region
        return t("qr_no_project", region=region_label(region)), None, None, False

    # человек из другого региона — ошибка, не отмечаем (Самарканд — только на самаркандские)
    if services.wrong_region(volunteer, project):
        return t("qr_wrong_region", name=escape(volunteer.fullname), pregion=region_label(volunteer.region),
                 project=escape(project.title), eregion=region_label(project.region)), None, None, False

    result, auto_added = services.check_in(volunteer, project)
    if result == "already":
        return t("qr_already", name=escape(volunteer.fullname), project=escape(project.title)), volunteer, None, False

    volunteer.refresh_from_db()
    success_text = t(
        "qr_success",
        name=escape(volunteer.fullname),
        project=escape(project.title),
        note=t("qr_auto_added") if auto_added else "",
        balance=volunteer.balance,
        scanner=escape(scanner_user.fullname),
        role=role_label(scanner_user.role),
    )
    return success_text, volunteer, project, True


async def show_qr_handler(message: types.Message):
    """Generates a personal QR code for the user"""
    await send_qr(message, message.from_user.id)


async def send_qr(message: types.Message, tg_id: int):
    """QR человека tg_id в чат message (нужно и из кнопки напоминания, где from_user — бот)."""
    bot_info = await message.bot.me  # кэшируется aiogram'ом, без лишнего запроса
    qr_link = f"https://t.me/{bot_info.username}?start=qr_{tg_id}"

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
        message, f"qr:{tg_id}:{bot_info.username}", _generate_qr,
        caption=t("qr_caption")
    )

def register_qr_handlers(dp: Dispatcher):
    dp.register_message_handler(show_qr_handler, text=variants("btn_qr"), state="*")
