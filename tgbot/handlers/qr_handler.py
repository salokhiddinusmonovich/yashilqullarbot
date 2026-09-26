
import qrcode
from html import escape
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from django.utils import timezone
from tgbot.i18n import t, variants, region_label, role_label
from tgbot.services.photo_cache import send_cached_photo

# ==========================================
# 1. QR CODE & ATTENDANCE LOGIC
# ==========================================

def _pick_project(volunteer, scanner):
    """
    Какое мероприятие сейчас идёт. Приоритет:
    1) сегодняшнее в регионе волонтёра, 2) сегодняшнее в регионе
    сканирующего, 3) единственное сегодняшнее вообще,
    4) ближайшее по дате активное в регионе волонтёра.
    """
    from app_telegram.models import EcoProject

    def regions(region):
        if region in ('tashkent_s', 'tashkent_v'):
            return ['tashkent_s', 'tashkent_v']
        return [region]

    today = timezone.localdate()
    todays = list(EcoProject.objects.filter(is_active=True, date__date=today).order_by('date'))

    for region in (volunteer.region, scanner.region):
        if region:
            match = [p for p in todays if p.region in regions(region)]
            if match:
                return match[0]
    if len(todays) == 1:
        return todays[0]

    active = EcoProject.objects.filter(is_active=True, region__in=regions(volunteer.region))
    now = timezone.now()
    return (
        active.filter(date__gte=now).order_by('date').first()
        or active.filter(date__lt=now).order_by('-date').first()
    )


@sync_to_async
def process_qr_logic(scanner_tg_id, target_tg_id):
    """
    Processes the QR code scan.
    Permission is granted to any role EXCEPT regular volunteers.

    Если волонтёр пришёл, но НЕ записался на мероприятие — записываем
    его автоматически сразу со статусом "attended", чтобы координатору
    не приходилось лезть на сайт и добавлять руками.

    Returns: (result_text, volunteer, project, confirmed)
      confirmed=True — посещение только что засчитано (надо уведомить волонтёра).
    """
    from app_telegram.models import TGUser, ProjectParticipation

    scanner_user = TGUser.objects.filter(tg_id=scanner_tg_id).first()

    if not scanner_user or (scanner_user.role == TGUser.Role.VOLUNTEER and not scanner_user.is_admin):
        return t("qr_no_rights"), None, None, False

    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return t("qr_user_not_found"), None, None, False

    project = _pick_project(volunteer, scanner_user)
    if not project:
        return t("qr_no_project", region=region_label(volunteer.region)), None, None, False

    participation, created = ProjectParticipation.objects.get_or_create(
        project=project, user=volunteer, defaults={'status': 'attended'}
    )

    if not created and participation.status == 'attended':
        return t("qr_already", name=escape(volunteer.fullname), project=escape(project.title)), volunteer, None, False

    if not created:
        participation.status = 'attended'
        participation.save()

    volunteer.refresh_from_db()

    success_text = t(
        "qr_success",
        name=escape(volunteer.fullname),
        project=escape(project.title),
        note=t("qr_auto_added") if created else "",
        balance=volunteer.balance,
        scanner=escape(scanner_user.fullname),
        role=role_label(scanner_user.role),
    )
    return success_text, volunteer, project, True


async def show_qr_handler(message: types.Message):
    """Generates a personal QR code for the user"""
    bot_info = await message.bot.me  # кэшируется aiogram'ом, без лишнего запроса
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
        caption=t("qr_caption")
    )

def register_qr_handlers(dp: Dispatcher):
    dp.register_message_handler(show_qr_handler, text=variants("btn_qr"), state="*")
