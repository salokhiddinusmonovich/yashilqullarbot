"""
📊 «Tadbir tugadi — natijalarni kiriting»: через IMPACT_AFTER_H часов (по умолчанию 3) после начала
мероприятия координаторам его региона приходит кнопка ввода итогов (tgbot/handlers/impact.py).
Один раз на мероприятие (imp:asked:<id>), только днём (9:00–22:00), только если итогов ещё нет.
Отключить: IMPACT_PROMPT=0 в .env.
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
AFTER_H = float(os.environ.get("IMPACT_AFTER_H", "3"))
ENABLED = os.environ.get("IMPACT_PROMPT", "1") != "0"


@sync_to_async
def _due(now):
    from app_telegram import impact
    from app_telegram.models import EcoProject
    evs = list(EcoProject.objects.filter(date__lte=now - timedelta(hours=AFTER_H), date__gte=now - timedelta(days=2)))
    done = impact.many([e.id for e in evs])
    return [(e, [u.tg_id for u in impact.reporters_for(e)]) for e in evs if e.id not in done]


async def send_prompts(bot, now=None) -> int:
    now = now or timezone.now()
    if not 9 <= timezone.localtime(now).hour < 22:
        return 0
    r = _aclient()
    sent = 0
    for p, tgs in await _due(now):
        if not tgs:
            continue
        try:
            if not await r.set(f"imp:asked:{p.id}", 1, nx=True, ex=30 * 86400):
                continue
        except Exception:
            continue
        langs = await langs_of(tgs)
        for tg in tgs:
            lang = langs.get(tg)
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton(t("imp_btn_enter", lang), callback_data=f"imp:{p.id}"))
            try:
                await bot.send_message(tg, t("imp_prompt", lang, title=escape(p.title)), reply_markup=kb)
                sent += 1
            except exceptions.RetryAfter as e:
                await asyncio.sleep(e.timeout)
            except exceptions.TelegramAPIError:
                pass
            await asyncio.sleep(0.05)
    return sent


async def impact_prompt_loop(bot):
    if not ENABLED:
        return
    await asyncio.sleep(50)
    while True:
        try:
            n = await send_prompts(bot)
            if n:
                log.info("impact prompts sent: %s", n)
        except Exception:
            log.exception("impact prompt loop")
        await asyncio.sleep(900)
