"""
Статистика бота для ежедневного отчёта админам: кто заблокировал бота,
кто разблокировал, кто был активен за день.

Хранится в Redis, а не в БД — чтобы не трогать схему, пока история
Django-миграций не синхронизирована с models.py (см. sql/*.sql).
Все ошибки Redis глотаются: статистика не должна ронять хендлеры.
"""
import logging
import os

from django.utils import timezone
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

_KEEP_DAYS = 40 * 24 * 3600  # дневные ключи живут 40 дней

_redis = None


def _client():
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            password=os.environ.get("REDIS_PASSWORD") or None,
            db=6,
            decode_responses=True,
        )
    return _redis


def _day(date=None) -> str:
    return (date or timezone.localdate()).isoformat()


async def _safe(coro_factory, default=None):
    try:
        return await coro_factory()
    except Exception as e:
        logger.warning("stats redis error: %s", e)
        return default


async def mark_active(tg_id: int):
    key = f"stats:active:{_day()}"

    async def _do():
        pipe = _client().pipeline()
        pipe.sadd(key, tg_id)
        pipe.expire(key, _KEEP_DAYS)
        await pipe.execute()

    await _safe(_do)


async def mark_blocked(tg_id: int):
    key = f"stats:blocked:{_day()}"

    async def _do():
        # sadd в общий сет возвращает 1 только если юзер ещё не числился
        # заблокировавшим — чтобы рассылка не считала одного человека дважды.
        if await _client().sadd("stats:blocked", tg_id):
            pipe = _client().pipeline()
            pipe.sadd(key, tg_id)
            pipe.expire(key, _KEEP_DAYS)
            await pipe.execute()

    await _safe(_do)


async def mark_unblocked(tg_id: int):
    key = f"stats:unblocked:{_day()}"

    async def _do():
        if await _client().srem("stats:blocked", tg_id):
            pipe = _client().pipeline()
            pipe.sadd(key, tg_id)
            pipe.expire(key, _KEEP_DAYS)
            await pipe.execute()

    await _safe(_do)


async def day_counts(date=None) -> dict:
    day = _day(date)

    async def _do():
        pipe = _client().pipeline()
        pipe.scard(f"stats:active:{day}")
        pipe.scard(f"stats:blocked:{day}")
        pipe.scard(f"stats:unblocked:{day}")
        pipe.scard("stats:blocked")
        active, blocked, unblocked, blocked_total = await pipe.execute()
        return {
            "active": active,
            "blocked": blocked,
            "unblocked": unblocked,
            "blocked_total": blocked_total,
        }

    return await _safe(_do, default={"active": "?", "blocked": "?", "unblocked": "?", "blocked_total": "?"})


async def claim_daily_report(date=None) -> bool:
    """True, если отчёт за этот день ещё не отправлялся (защита от дублей при рестарте)."""
    return bool(await _safe(
        lambda: _client().set(f"stats:report_sent:{_day(date)}", 1, nx=True, ex=3 * 24 * 3600),
        default=True,
    ))
