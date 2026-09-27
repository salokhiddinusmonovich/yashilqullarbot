"""
Напоминания о мероприятиях — бесплатно, внутри бота.

  • накануне в REMIND_HOUR (по умолчанию 19:00 по Ташкенту) — всем, кто записан на завтра;
  • за ~2 часа до начала.
В сообщении кнопки «🌿 QR-kod» и «❌ Kelolmayman» (освобождает место —
координатор видит это в карточке мероприятия и в отчёте).

Кому уже отправили — множество rem:<вид>:<id мероприятия> в Redis (db 6),
поэтому перезапуск бота не приводит к повторным сообщениям.
"""
import asyncio
import logging
import os
from datetime import timedelta
from html import escape

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from django.utils import timezone

from tgbot.i18n import t
from .lang import _aclient, langs_of

log = logging.getLogger(__name__)
REMIND_HOUR = int(os.environ.get("REMIND_HOUR", "19"))
CHECK_EVERY = 300  # сек


def kb(project_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton(t("rem_btn_qr", lang), callback_data="rem:qr"),
        InlineKeyboardButton(t("rem_btn_no", lang), callback_data=f"rem:no:{project_id}"),
    )


@sync_to_async
def _due(now):
    """[(вид, мероприятие, [(tg_id, ...)])] — кому что пора отправить."""
    from app_telegram.models import EcoProject, ProjectParticipation
    local = timezone.localtime(now)
    out = []
    # за 2 часа: начало через 1:45…2:15 (с запасом на интервал проверки)
    soon = EcoProject.objects.filter(date__gt=now + timedelta(minutes=100), date__lte=now + timedelta(minutes=135))
    for p in soon:
        out.append(("2h", p))
    # накануне: с REMIND_HOUR до полуночи — все мероприятия завтрашнего дня
    if local.hour >= REMIND_HOUR:
        tomorrow = (local + timedelta(days=1)).date()
        for p in EcoProject.objects.filter(date__date=tomorrow):
            out.append(("day", p))
    res = []
    for kind, p in out:
        tg_ids = list(ProjectParticipation.objects.filter(project=p, status='approved', user__tg_id__isnull=False)
                      .values_list('user__tg_id', flat=True))
        if tg_ids:
            res.append((kind, p, tg_ids))
    return res


async def send_due(bot, now=None):
    now = now or timezone.now()
    r = _aclient()
    sent = 0
    for kind, p, tg_ids in await _due(now):
        key = f"rem:{kind}:{p.id}"
        try:
            done = {int(x) for x in await r.smembers(key)}
        except Exception:
            continue   # без Redis не шлём — иначе можно заспамить повторами
        todo = [x for x in tg_ids if x not in done]
        if not todo:
            continue
        langs = await langs_of(todo)
        when = timezone.localtime(p.date)
        for tg in todo:
            lang = langs.get(tg)
            text = t(f"rem_{kind}", lang, title=escape(p.title), date=when.strftime('%d.%m'), time=when.strftime('%H:%M'),
                     place=escape(p.location_name or "—"))
            if p.chat_link:
                text += t("rem_group", lang, link=p.chat_link)
            try:
                await bot.send_message(tg, text, reply_markup=kb(p.id, lang), disable_web_page_preview=True)
                sent += 1
            except exceptions.RetryAfter as e:
                await asyncio.sleep(e.timeout)
            except exceptions.TelegramAPIError:
                pass   # заблокировал бота и т.п. — просто пропускаем
            await r.sadd(key, tg)
            await r.expire(key, 3 * 86400)
            await asyncio.sleep(0.05)
    return sent


async def reminders_loop(bot):
    await asyncio.sleep(20)
    while True:
        try:
            n = await send_due(bot)
            if n:
                log.info("reminders sent: %s", n)
        except Exception:
            log.exception("reminders loop")
        await asyncio.sleep(CHECK_EVERY)
