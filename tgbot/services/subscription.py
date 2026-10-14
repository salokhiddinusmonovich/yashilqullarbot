"""
📢 Обязательная подписка на канал @yashilqollar — проверка для всего бота (tgbot/middlewares/subscription.py).

Подписан → помним 30 минут (Redis sub:ok:<tg>), чтобы не спрашивать Telegram на каждое нажатие.
Telegram не ответил / бот потерял права админа в канале → НЕ блокируем людей (пишем в лог).
"""
import logging

from aiogram.utils import exceptions

from .lang import _aclient

log = logging.getLogger(__name__)
CHANNEL = "@yashilqollar"
CHANNEL_URL = "https://t.me/yashilqollar"
OK_TTL = 30 * 60
MEMBER_STATUSES = ("creator", "administrator", "member", "restricted")


async def is_member(bot, tg_id: int) -> bool | None:
    """True / False — подписан или нет; None — проверить не удалось."""
    try:
        m = await bot.get_chat_member(chat_id=CHANNEL, user_id=tg_id)
    except exceptions.BadRequest as e:
        if "user not found" in str(e).lower() or "participant_id_invalid" in str(e).lower():
            return False                      # человека нет в канале
        log.warning("subscription check failed (бот — админ канала %s?): %s", CHANNEL, e)
        return None
    except Exception as e:
        log.warning("subscription check failed: %s", e)
        return None
    if m.status == "restricted":
        return bool(getattr(m, "is_member", True))
    return m.status in MEMBER_STATUSES


async def check(bot, tg_id: int, fresh: bool = False) -> bool:
    """Можно ли пользоваться ботом. fresh=True — не смотреть в кэш (кнопка «✅ Я подписался»)."""
    r = _aclient()
    key = f"sub:ok:{tg_id}"
    if not fresh:
        try:
            if await r.get(key):
                return True
        except Exception:
            pass
    ok = await is_member(bot, tg_id)
    if ok is None:
        return True                           # сбой проверки — людей не блокируем
    if ok:
        try:
            await r.set(key, 1, ex=OK_TTL)
        except Exception:
            pass
    return ok


async def remember_start(tg_id: int, args: str):
    """Запомнить, с какой ссылкой человек пришёл (вход с сайта, QR, «пригласи друга», «Iflos joy»)."""
    try:
        await _aclient().set(f"sub:start:{tg_id}", args or "", ex=86400)
    except Exception:
        pass


async def pop_start(tg_id: int) -> str:
    try:
        r = _aclient()
        v = await r.get(f"sub:start:{tg_id}")
        await r.delete(f"sub:start:{tg_id}")
        return v or ""
    except Exception:
        return ""
