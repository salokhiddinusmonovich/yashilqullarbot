"""
📅 Еженедельный дайджест: по понедельникам в DIGEST_HOUR (по умолчанию 10:00, Ташкент)
каждому волонтёру — мероприятия его региона на ближайшие 7 дней, куда он ещё не записан,
с кнопками «✅ Записаться» (тот же обработчик evreg:, что и в меню мероприятий).

Нет мероприятий — ничего не шлём. Кому отправлено — digest:sent:<год-неделя> в Redis
(перезапуск не дублирует). Отписка — кнопка «🔕» (digest:off), вернуть — /digest.
Отключить совсем: DIGEST_AUTO=0 в .env.
"""
import asyncio
import logging
import os
from datetime import timedelta
from html import escape

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from django.utils import timezone

from tgbot.i18n import t
from .lang import _aclient, langs_of

log = logging.getLogger(__name__)
DIGEST_HOUR = int(os.environ.get("DIGEST_HOUR", "10"))
ENABLED = os.environ.get("DIGEST_AUTO", "1") != "0"
WEEKDAYS = {"uz": ["du", "se", "chor", "pay", "ju", "shan", "yak"], "ru": ["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
            "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}


def week_key(now=None) -> str:
    y, w, _ = timezone.localtime(now or timezone.now()).isocalendar()
    return f"{y}-{w:02d}"


@sync_to_async
def _plan(now):
    """[(tg_id, [события])] — только тем, у кого есть что предложить."""
    from app_telegram.models import TGUser, EcoProject, ProjectParticipation
    from app_telegram.services import region_group
    events = list(EcoProject.objects.filter(is_active=True, date__gte=now, date__lte=now + timedelta(days=7))
                  .annotate(taken=Count('participants', filter=~Q(participants__status='rejected'))).order_by('date'))
    if not events:
        return []
    by_region = {}
    for e in events:
        by_region.setdefault(e.region, []).append(e)
    mine = {}
    for uid, pid in ProjectParticipation.objects.filter(project__in=events).values_list('user__tg_id', 'project_id'):
        mine.setdefault(uid, set()).add(pid)
    out = []
    for tg, region in TGUser.objects.filter(tg_id__isnull=False).exclude(region__isnull=True).exclude(region='').values_list('tg_id', 'region'):
        evs = [e for r in region_group(region) for e in by_region.get(r, []) if e.id not in mine.get(tg, set())]
        if evs:
            out.append((tg, sorted(evs, key=lambda e: e.date)[:5]))
    return out


def render(evs, lang):
    lines = [t("digest_title", lang), ""]
    for e in evs:
        d = timezone.localtime(e.date)
        seats = t("digest_full", lang) if e.taken >= e.max_participants else f"👥 {e.taken}/{e.max_participants}"
        lines.append(f"• <b>{d:%d.%m}</b> ({WEEKDAYS.get(lang, WEEKDAYS['uz'])[d.weekday()]}) {d:%H:%M} — <b>{escape(e.title)}</b>\n"
                     f"   📍 {escape(e.location_name or '—')} · {seats}")
    lines += ["", t("digest_hint", lang)]
    kb = InlineKeyboardMarkup(row_width=1)
    for e in evs:
        kb.add(InlineKeyboardButton(f"✅ {e.title[:34]}", callback_data=f"evreg:{e.id}"))
    kb.add(InlineKeyboardButton(t("digest_off_btn", lang), callback_data="digest:off"))
    return "\n".join(lines), kb


async def send_digest(bot, now=None, force=False):
    now = now or timezone.now()
    local = timezone.localtime(now)
    if not force and (local.weekday() != 0 or local.hour < DIGEST_HOUR):
        return 0
    r = _aclient()
    wk = week_key(now)
    sent_key = f"digest:sent:{wk}"
    try:
        done = {int(x) for x in await r.smembers(sent_key)}
        off = {int(x) for x in await r.smembers("digest:off")}
    except Exception:
        return 0
    todo = [(tg, evs) for tg, evs in await _plan(now) if tg not in done and tg not in off]
    if not todo:
        return 0
    langs = await langs_of([tg for tg, _ in todo])
    sent = 0
    for tg, evs in todo:
        text, kb = render(evs, langs.get(tg))
        try:
            await bot.send_message(tg, text, reply_markup=kb, disable_web_page_preview=True)
            sent += 1
        except exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
            continue
        except exceptions.TelegramAPIError:
            pass
        await r.sadd(sent_key, tg)
        await r.expire(sent_key, 10 * 86400)
        await asyncio.sleep(0.05)
    return sent


async def digest_loop(bot):
    if not ENABLED:
        return
    await asyncio.sleep(60)
    while True:
        try:
            n = await send_digest(bot)
            if n:
                log.info("digest sent: %s", n)
        except Exception:
            log.exception("digest loop")
        await asyncio.sleep(900)
