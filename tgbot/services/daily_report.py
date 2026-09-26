"""
Ежедневный отчёт админам: сколько пришло юзеров, сколько заблокировали
бота, кто был активен, записи на мероприятия, посещения, отзывы.

Шлётся каждый день в DAILY_REPORT_HOUR (по умолчанию 21:00, Asia/Tashkent)
всем TGUser.is_admin=True + ADMIN_IDS из .env. Этот же текст показывает
кнопка "📊 Statistika" в /admin. Текст — на языке каждого админа.
"""
import asyncio
import logging
import os
from datetime import timedelta
from html import escape

from asgiref.sync import sync_to_async
from django.db.models import Avg, Count, Q
from django.utils import timezone

from tgbot.i18n import t
from tgbot.services import stats
from tgbot.services.lang import langs_of

logger = logging.getLogger(__name__)

REPORT_HOUR = int(os.environ.get("DAILY_REPORT_HOUR", "21"))


@sync_to_async
def _db_numbers(day):
    from app_telegram.models import TGUser, ProjectParticipation, EventFeedback, EcoProject

    new_users = TGUser.objects.filter(created__date=day)
    by_provider = dict(new_users.values_list("auth_provider").annotate(c=Count("id")))
    week_ago = day - timedelta(days=6)

    feedback = EventFeedback.objects.filter(created_at__date=day).aggregate(c=Count("id"), avg=Avg("rating"))

    now = timezone.now()
    upcoming = list(
        EcoProject.objects.filter(is_active=True, date__gte=now, date__lte=now + timedelta(days=7))
        .annotate(
            registered=Count("participants", filter=~Q(participants__status="rejected")),
        )
        .order_by("date")[:10]
    )

    return {
        "total": TGUser.objects.count(),
        "total_tg": TGUser.objects.filter(tg_id__isnull=False).count(),
        "new": new_users.count(),
        "new_week": TGUser.objects.filter(created__date__gte=week_ago, created__date__lte=day).count(),
        "by_provider": by_provider,
        "registrations": ProjectParticipation.objects.filter(applied_at__date=day).count(),
        "attended": ProjectParticipation.objects.filter(project__date__date=day, status="attended").count(),
        "feedback_count": feedback["c"],
        "feedback_avg": feedback["avg"],
        "upcoming": upcoming,
    }


async def report_data(day=None) -> dict:
    day = day or timezone.localdate()
    db = await _db_numbers(day)
    db["redis"] = await stats.day_counts(day)
    db["day"] = day
    return db


def render_report(db: dict, lang: str = None) -> str:
    """Цифры считаются один раз, текст — на языке каждого админа."""
    r = db["redis"]
    providers = db["by_provider"]
    provider_line = ", ".join(
        f"{label}: {providers[key]}"
        for key, label in (("telegram", t("src_bot", lang)), ("email", t("src_site", lang)), ("google", "Google"))
        if providers.get(key)
    )

    lines = [
        t("rep_title", lang, date=db["day"].strftime('%d.%m.%Y')),
        "",
        t("rep_users", lang, total=db["total"], tg=db["total_tg"]),
        t("rep_new", lang, n=db["new"]) + (f" ({provider_line})" if provider_line else ""),
        t("rep_week", lang, n=db["new_week"]),
        t("rep_active", lang, n=r["active"]),
        t("rep_blocked", lang, b=r["blocked"], u=r["unblocked"], total=r["blocked_total"]),
        "",
        t("rep_regs", lang, n=db["registrations"]),
        t("rep_attended", lang, n=db["attended"]),
    ]
    if db["feedback_count"]:
        lines.append(t("rep_feedback", lang, n=db["feedback_count"], avg=f"{db['feedback_avg']:.1f}"))

    if db["upcoming"]:
        lines += ["", t("rep_upcoming", lang)]
        for p in db["upcoming"]:
            date = timezone.localtime(p.date).strftime("%d.%m %H:%M")
            lines.append(f"• {escape(p.title)} — {date} — {p.registered}/{p.max_participants}")

    lines += ["", t("rep_note", lang)]
    return "\n".join(lines)


async def build_report(day=None, lang: str = None) -> str:
    return render_report(await report_data(day), lang)


@sync_to_async
def admin_ids(bot) -> set:
    from app_telegram.models import TGUser
    ids = set(TGUser.objects.filter(is_admin=True, tg_id__isnull=False).values_list("tg_id", flat=True))
    ids.update(bot["config"].tg_bot.admin_ids)
    return ids


async def send_daily_report(bot):
    data = await report_data()
    ids = await admin_ids(bot)
    langs = await langs_of(ids)
    for admin_id in ids:
        try:
            await bot.send_message(admin_id, render_report(data, langs.get(admin_id)), parse_mode="HTML")
        except Exception as e:
            logger.warning("Daily report to %s failed: %s", admin_id, e)
        await asyncio.sleep(0.05)


async def daily_report_loop(bot):
    while True:
        now = timezone.localtime()
        target = now.replace(hour=REPORT_HOUR, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            if await stats.claim_daily_report():
                await send_daily_report(bot)
        except Exception as e:
            logger.exception("Daily report failed: %s", e)
        await asyncio.sleep(60)
