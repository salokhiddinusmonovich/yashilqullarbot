"""
Ежедневный отчёт админам: сколько пришло юзеров, сколько заблокировали
бота, кто был активен, записи на мероприятия, посещения, отзывы.

Шлётся каждый день в DAILY_REPORT_HOUR (по умолчанию 21:00, Asia/Tashkent)
всем TGUser.is_admin=True + ADMIN_IDS из .env. Этот же текст показывает
кнопка "📊 Statistika" в /admin.
"""
import asyncio
import logging
import os
from datetime import timedelta
from html import escape

from asgiref.sync import sync_to_async
from django.db.models import Avg, Count, Q
from django.utils import timezone

from tgbot.services import stats

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


async def build_report(day=None) -> str:
    day = day or timezone.localdate()
    db = await _db_numbers(day)
    r = await stats.day_counts(day)

    providers = db["by_provider"]
    provider_line = ", ".join(
        f"{label}: {providers[key]}"
        for key, label in (("telegram", "bot"), ("email", "sayt"), ("google", "Google"))
        if providers.get(key)
    )

    lines = [
        f"📊 <b>Kunlik hisobot — {day.strftime('%d.%m.%Y')}</b>",
        "",
        f"👥 <b>Foydalanuvchilar:</b> {db['total']} (Telegram bilan: {db['total_tg']})",
        f"🆕 Bugun qo'shildi: <b>+{db['new']}</b>" + (f" ({provider_line})" if provider_line else ""),
        f"📈 Oxirgi 7 kunda: +{db['new_week']}",
        f"🟢 Bugun botdan foydalandi: <b>{r['active']}</b>",
        f"🚫 Bugun botni bloklagan: <b>{r['blocked']}</b> · qaytgan: {r['unblocked']} · jami bloklagan: {r['blocked_total']}",
        "",
        f"📝 Bugun tadbirga yozilganlar: <b>{db['registrations']}</b>",
        f"✅ Bugungi tadbirlarda tasdiqlangan: <b>{db['attended']}</b>",
    ]
    if db["feedback_count"]:
        lines.append(f"⭐ Yangi fikrlar: {db['feedback_count']} (o'rtacha {db['feedback_avg']:.1f})")

    if db["upcoming"]:
        lines += ["", "📅 <b>Yaqin 7 kundagi tadbirlar:</b>"]
        for p in db["upcoming"]:
            date = timezone.localtime(p.date).strftime("%d.%m %H:%M")
            lines.append(f"• {escape(p.title)} — {date} — {p.registered}/{p.max_participants}")

    lines += ["", "<i>«Bloklagan» hisobi shu funksiya qo'shilgan kundan boshlab yuritiladi.</i>"]
    return "\n".join(lines)


@sync_to_async
def admin_ids(bot) -> set:
    from app_telegram.models import TGUser
    ids = set(TGUser.objects.filter(is_admin=True, tg_id__isnull=False).values_list("tg_id", flat=True))
    ids.update(bot["config"].tg_bot.admin_ids)
    return ids


async def send_daily_report(bot):
    text = await build_report()
    for admin_id in await admin_ids(bot):
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
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
