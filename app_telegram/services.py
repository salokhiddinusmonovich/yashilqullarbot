"""
Общая бизнес-логика мероприятий — одна на бота, Mini App и админку.
Здесь только работа с БД (синхронно), без текстов и без Telegram:
тексты — в местах вызова (tgbot/i18n.py, фронт Mini App).
"""
import re

from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from .models import TGUser, EcoProject, ProjectParticipation

TASHKENT = ('tashkent_s', 'tashkent_v')

QR_RE = re.compile(r"qr_(\d+)")


def region_group(region):
    """Ташкент-город и область — одна группа мероприятий."""
    if region in TASHKENT:
        return list(TASHKENT)
    return [region] if region else []


def is_staff(user: TGUser) -> bool:
    """
    Кто может сканировать QR и видит аналитику мероприятия (бот, Mini App):
    решает ТОЛЬКО роль — любая, кроме «Волонтёр» (координаторы, IT,
    медиа, организаторы, основатель).

    Галочка is_admin сюда НЕ даёт доступа — она только про админ-панель
    со статистикой (/admin в боте). Админу, которому нужен сканер, нужно
    дать роль.
    """
    return bool(user) and user.role != TGUser.Role.VOLUNTEER


def with_counts(qs):
    return qs.annotate(
        registered=Count('participants', filter=~Q(participants__status='rejected')),
        attended=Count('participants', filter=Q(participants__status='attended')),
    )


def scan_regions(user: TGUser):
    """
    Мероприятия каких регионов человек может сканировать.
    Координатор, медиа, IT и т.д. — только своего региона (Ташкент-город
    и область — одна группа). None — без ограничений: основатель, или
    регион в профиле не указан (тогда фильтровать не по чему).
    """
    if user.role == TGUser.Role.FOUNDER or not user.region:
        return None
    return region_group(user.region)


def can_scan_project(user: TGUser, project: EcoProject) -> bool:
    allowed = scan_regions(user)
    return allowed is None or project.region in allowed


def pick_project(volunteer: TGUser, scanner: TGUser):
    """
    Какое мероприятие сейчас идёт (для скана из бота, где мероприятие
    не выбрано явно). Только среди регионов, которые сканирующему можно
    (scan_regions). Приоритет: сегодняшнее в регионе волонтёра →
    сегодняшнее в регионе сканирующего → единственное сегодняшнее →
    ближайшее по дате активное.
    """
    allowed = scan_regions(scanner)
    today = timezone.localdate()
    todays = [
        p for p in EcoProject.objects.filter(is_active=True, date__date=today).order_by('date')
        if allowed is None or p.region in allowed
    ]

    for region in (volunteer.region, scanner.region):
        if region:
            match = [p for p in todays if p.region in region_group(region)]
            if match:
                return match[0]
    if len(todays) == 1:
        return todays[0]

    active = EcoProject.objects.filter(is_active=True, region__in=allowed or region_group(volunteer.region))
    now = timezone.now()
    return (
        active.filter(date__gte=now).order_by('date').first()
        or active.filter(date__lt=now).order_by('-date').first()
    )


def check_in(volunteer: TGUser, project: EcoProject):
    """
    Отметить, что человек пришёл. Не записан — записываем сразу
    со статусом attended (+10 баллов внутри ProjectParticipation.save()).

    Возвращает (result, auto_added):
      result: "ok" — отмечен сейчас, "already" — уже был отмечен.
    """
    participation, created = ProjectParticipation.objects.get_or_create(
        project=project, user=volunteer, defaults={'status': 'attended'}
    )
    if created:
        return "ok", True
    if participation.status == 'attended':
        return "already", False
    participation.status = 'attended'
    participation.save()
    return "ok", False


def parse_qr(text: str):
    """tg_id из содержимого QR (https://t.me/<bot>?start=qr_<tg_id>) или None."""
    m = QR_RE.search(text or "")
    return int(m.group(1)) if m else None


def join_event(user: TGUser, project_id: int):
    """
    Запись на мероприятие. Возвращает (code, project):
    ok / already / gone / full / region.
    "region" — мероприятие не в регионе человека: записываться можно только
    в своём (Ташкент-город и область — один регион). Смотреть чужие можно.
    Проверку подписки на канал делает вызывающий (это сетевой запрос).
    """
    project = EcoProject.objects.filter(id=project_id, is_active=True).first()
    if not project:
        return "gone", None
    if ProjectParticipation.objects.filter(user=user, project=project).exists():
        return "already", project
    if project.region not in region_group(user.region):
        return "region", project
    if project.participants.exclude(status='rejected').count() >= project.max_participants:
        return "full", project
    _, created = ProjectParticipation.objects.get_or_create(
        user=user, project=project, defaults={'status': 'approved'}
    )
    return ("ok" if created else "already"), project


def user_search_q(text: str):
    """
    Поиск человека одной строкой: @username, телефон (любой формат),
    email, Telegram ID или часть имени. Общий для бота и Mini App.
    """
    text = (text or "").strip()
    compact = re.sub(r"[\s+\-()]", "", text)
    if text.startswith("@"):
        return Q(username__iexact=text[1:])
    if "@" in text and "." in text:
        return Q(email__iexact=text)
    if compact.isdigit() and len(compact) >= 5:
        # телефон в базе бывает в разных форматах — ищем по последним 9 цифрам
        return Q(phone__endswith=compact[-9:]) | Q(tg_id=int(compact))
    return Q(fullname__icontains=text) | Q(username__iexact=text)


def same_region(a, b) -> bool:
    """Один регион (Ташкент-город и область — одно целое)."""
    return bool(a and b) and b in region_group(a)


@transaction.atomic
def move_participations(participations, target: EcoProject):
    """
    Перенести отметки на другое мероприятие (координатор сканировал,
    выбрав не то мероприятие). Баллы не дублируются и не теряются:
      • на целевом мероприятии записи нет — просто меняем мероприятие;
      • запись есть — объединяем: «пришёл» переходит на неё, лишнюю удаляем,
        а если человек был отмечен на обоих — возвращаем лишние 10 баллов.
    Возвращает список (participation_на_целевом, было_ли_attended) для уведомлений.
    """
    moved = []
    for p in participations.select_related('user'):
        if p.project_id == target.id:
            continue
        existing = ProjectParticipation.objects.filter(user=p.user, project=target).first()
        if existing is None:
            ProjectParticipation.objects.filter(pk=p.pk).update(project=target)   # без save(): баллы не трогаем
            moved.append((p.user, p.status == 'attended'))
            continue
        if p.status == 'attended':
            if existing.status == 'attended':
                TGUser.objects.filter(pk=p.user_id, balance__gte=10).update(balance=F('balance') - 10)
            else:
                ProjectParticipation.objects.filter(pk=existing.pk).update(status='attended')
        p.delete()
        moved.append((p.user, p.status == 'attended'))
    return moved


@transaction.atomic
def undo_check_in(volunteer: TGUser, project: EcoProject, auto_added: bool):
    """
    «Отменить» только что сделанную отметку. Записан автоматически при
    скане — удаляем запись и забираем 10 баллов; был записан заранее —
    возвращаем статус «записан» (минус 10 баллов внутри save()).
    """
    p = ProjectParticipation.objects.filter(user=volunteer, project=project).first()
    if not p or p.status != 'attended':
        return False
    if auto_added:
        TGUser.objects.filter(pk=volunteer.pk, balance__gte=10).update(balance=F('balance') - 10)
        p.delete()
    else:
        p.status = 'approved'
        p.save()
    return True
