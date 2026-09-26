"""
Язык юзера: хранится в Redis (lang:<tg_id>) + кэш в памяти процесса бота.

В Redis, а не в TGUser — чтобы не трогать схему БД, пока миграции не
синхронизированы (см. sql/*.sql). Django-админка (уведомления о роли,
рассылки из админки) читает тот же ключ через get_lang_sync().

Если язык не выбран — возвращается None, и вызывающий решает сам
(обычно DEFAULT_LANG = узбекский).
"""
import logging
import os
import time

import redis
from redis import asyncio as aioredis

from tgbot.i18n import LANGS, DEFAULT_LANG

logger = logging.getLogger(__name__)

# tg_id -> (lang, когда закэшировано). Короткий TTL: язык может поменяться
# и из Mini App (через Redis), бот должен это увидеть почти сразу.
_cache: dict[int, tuple] = {}
_TTL = 30


def _cached(tg_id):
    hit = _cache.get(tg_id)
    if hit and time.monotonic() - hit[1] < _TTL:
        return hit[0]
    return None


def _remember(tg_id, lang):
    _cache[tg_id] = (lang, time.monotonic())
_async = None
_sync = None


def _params():
    return dict(
        host=os.environ.get("REDIS_HOST", "redis"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        password=os.environ.get("REDIS_PASSWORD") or None,
        db=6,
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2,
    )


def _aclient():
    global _async
    if _async is None:
        _async = aioredis.Redis(**_params())
    return _async


def _sclient():
    global _sync
    if _sync is None:
        _sync = redis.Redis(**_params())
    return _sync


async def get_lang(tg_id: int) -> str | None:
    hit = _cached(tg_id)
    if hit:
        return hit
    try:
        lang = await _aclient().get(f"lang:{tg_id}")
    except Exception as e:
        logger.warning("lang redis error: %s", e)
        return None
    if lang in LANGS:
        _remember(tg_id, lang)
        return lang
    return None


async def set_lang(tg_id: int, lang: str):
    if lang not in LANGS:
        return
    _remember(tg_id, lang)
    try:
        await _aclient().set(f"lang:{tg_id}", lang)
    except Exception as e:
        logger.warning("lang redis error: %s", e)


async def lang_of(tg_id: int) -> str:
    """Язык получателя для уведомлений — всегда что-то возвращает."""
    return await get_lang(tg_id) or DEFAULT_LANG


async def langs_of(tg_ids) -> dict[int, str]:
    """Языки сразу для многих — одним запросом в Redis (для рассылок)."""
    tg_ids = [i for i in tg_ids if i]
    result = {i: _cached(i) for i in tg_ids if _cached(i)}
    missing = [i for i in tg_ids if i not in result]
    if missing:
        try:
            values = await _aclient().mget([f"lang:{i}" for i in missing])
        except Exception as e:
            logger.warning("lang redis error: %s", e)
            values = [None] * len(missing)
        for i, v in zip(missing, values):
            if v in LANGS:
                _remember(i, v)
            result[i] = v if v in LANGS else DEFAULT_LANG
    return result


# ── синхронные версии — для Django-админки ──

def lang_of_sync(tg_id: int) -> str:
    try:
        lang = _sclient().get(f"lang:{tg_id}")
    except Exception as e:
        logger.warning("lang redis error: %s", e)
        return DEFAULT_LANG
    return lang if lang in LANGS else DEFAULT_LANG


def set_lang_sync(tg_id: int, lang: str):
    if lang not in LANGS:
        return
    try:
        _sclient().set(f"lang:{tg_id}", lang)
    except Exception as e:
        logger.warning("lang redis error: %s", e)


def langs_of_sync(tg_ids) -> dict[int, str]:
    tg_ids = [i for i in tg_ids if i]
    if not tg_ids:
        return {}
    try:
        values = _sclient().mget([f"lang:{i}" for i in tg_ids])
    except Exception as e:
        logger.warning("lang redis error: %s", e)
        values = [None] * len(tg_ids)
    return {i: (v if v in LANGS else DEFAULT_LANG) for i, v in zip(tg_ids, values)}
