"""
🎓 Автоматическая отправка сертификатов — на следующее утро после мероприятия.

Каждые 10 минут после CERT_HOUR (по умолчанию 10:00 по Ташкенту): мероприятия
за последние 3 дня, которые уже прошли вчера или раньше, — всем со статусом
«пришёл», кому ещё не отправляли, бот присылает PDF. Кому отправлено —
множество cert:sent:<id мероприятия> в Redis (перезапуск не дублирует).
Старые мероприятия сюда не попадают — для них в админке «📣 Eski tadbirlar»
(одно сообщение каждому, сертификаты — в /sertifikat и в приложении).
Отключить: CERT_AUTO=0 в .env.
"""
import asyncio
import logging
import os
from datetime import timedelta
from html import escape
from io import BytesIO

from aiogram.types import InputFile
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from django.utils import timezone

from tgbot.i18n import t
from .lang import _aclient, langs_of

log = logging.getLogger(__name__)
CERT_HOUR = int(os.environ.get("CERT_HOUR", "10"))
ENABLED = os.environ.get("CERT_AUTO", "1") != "0"


@sync_to_async
def _due(now):
    from app_telegram.models import EcoProject, ProjectParticipation
    today = timezone.localtime(now).date()
    events = EcoProject.objects.filter(date__date__lt=today, date__date__gte=today - timedelta(days=3))
    out = []
    for p in events:
        pps = list(ProjectParticipation.objects.filter(project=p, status='attended', user__tg_id__isnull=False)
                   .select_related('user', 'project'))
        if pps:
            out.append((p, pps))
    return out


@sync_to_async
def _pdf(pp):
    from app_telegram import certificates as C
    return C.to_pdf(C.render_for(pp)), C.filename(pp), C.number_of(pp)


async def send_due(bot, now=None):
    now = now or timezone.now()
    if timezone.localtime(now).hour < CERT_HOUR:
        return 0
    r = _aclient()
    sent = 0
    for p, pps in await _due(now):
        key = f"cert:sent:{p.id}"
        try:
            done = {int(x) for x in await r.smembers(key)}
        except Exception:
            continue
        todo = [pp for pp in pps if pp.user.tg_id not in done]
        if not todo:
            continue
        langs = await langs_of([pp.user.tg_id for pp in todo])
        for pp in todo:
            tg = pp.user.tg_id
            try:
                data, fname, number = await _pdf(pp)
                await bot.send_document(tg, InputFile(BytesIO(data), filename=fname),
                                        caption=t("cert_caption", langs.get(tg), title=escape(p.title), number=number))
                sent += 1
            except exceptions.RetryAfter as e:
                await asyncio.sleep(e.timeout)
                continue          # не помечаем — отправим на следующем круге
            except exceptions.TelegramAPIError:
                pass              # заблокировал бота — не пытаемся снова
            except Exception:
                log.exception("certificate render/send")
                continue
            await r.sadd(key, tg)
            await r.expire(key, 30 * 86400)
            await asyncio.sleep(0.1)
    return sent


async def certificates_loop(bot):
    if not ENABLED:
        return
    await asyncio.sleep(40)
    while True:
        try:
            n = await send_due(bot)
            if n:
                log.info("certificates sent: %s", n)
        except Exception:
            log.exception("certificates loop")
        await asyncio.sleep(600)
