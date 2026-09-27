"""
🎁 Рассылка «итоги года»: в WRAPPED_DAY (ММ-ДД, по умолчанию 12-20) с WRAPPED_HOUR (12:00)
каждому, кто в этом году был хотя бы на одном мероприятии, — картинка-сторис и кнопка «открыть историю».
Кому отправлено — wr:sent:<год> в Redis (перезапуск не дублирует). Отключить: WRAPPED_AUTO=0.
"""
import asyncio
import logging
import os
from io import BytesIO

from aiogram.types import InputFile
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from django.utils import timezone

from tgbot.i18n import t
from .lang import _aclient, langs_of

log = logging.getLogger(__name__)
DAY = os.environ.get("WRAPPED_DAY", "12-20")
HOUR = int(os.environ.get("WRAPPED_HOUR", "12"))
ENABLED = os.environ.get("WRAPPED_AUTO", "1") != "0"


@sync_to_async
def _people(year: int):
    from app_telegram.models import TGUser
    return list(TGUser.objects.filter(tg_id__isnull=False, participations__status='attended',
                                      participations__project__date__year=year).distinct())


@sync_to_async
def _image(user, year, lang):
    from app_telegram import wrapped
    return wrapped.image_for(user, year, lang)


def keyboard(bot, lang):
    from tgbot.handlers.miniapp import app_url
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    url = app_url(bot, wrapped=1) if hasattr(bot, "get") and bot.get("config") else None
    return InlineKeyboardMarkup().add(InlineKeyboardButton(t("wr_btn_open", lang), web_app=WebAppInfo(url=url))) if url else None


async def send_one(bot, user, year: int, lang: str):
    data = await _image(user, year, lang)
    await bot.send_photo(user.tg_id, InputFile(BytesIO(data), filename=f"YashilQollar_{year}.jpg"),
                         caption=t("wr_caption", lang, y=year), reply_markup=keyboard(bot, lang))


async def send_due(bot, now=None) -> int:
    now = timezone.localtime(now or timezone.now())
    m, d = (int(x) for x in DAY.split("-"))
    if (now.month, now.day) < (m, d) or now.month != m or now.hour < HOUR:
        return 0
    year = now.year
    r = _aclient()
    key = f"wr:sent:{year}"
    try:
        done = {int(x) for x in await r.smembers(key)}
    except Exception:
        return 0
    people = [u for u in await _people(year) if u.tg_id not in done]
    if not people:
        return 0
    langs = await langs_of([u.tg_id for u in people])
    sent = 0
    for u in people:
        try:
            await send_one(bot, u, year, langs.get(u.tg_id) or "uz")
            sent += 1
        except exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
            continue                      # не помечаем — отправим на следующем круге
        except exceptions.TelegramAPIError:
            pass                          # заблокировал бота
        except Exception:
            log.exception("wrapped send")
            continue
        await r.sadd(key, u.tg_id)
        await r.expire(key, 120 * 86400)
        await asyncio.sleep(0.08)
    return sent


async def wrapped_loop(bot):
    if not ENABLED:
        return
    await asyncio.sleep(70)
    while True:
        try:
            n = await send_due(bot)
            if n:
                log.info("wrapped sent: %s", n)
        except Exception:
            log.exception("wrapped loop")
        await asyncio.sleep(900)
