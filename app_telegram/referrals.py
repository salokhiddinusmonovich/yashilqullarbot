"""
«Пригласи друга». Ссылка https://t.me/<бот>?start=ref_<tg_id пригласившего>.

Новый человек открыл бота по ссылке → запоминаем, кто пригласил (только если
его ещё нет в базе и это не он сам). Когда друг впервые приходит на мероприятие
(статус «пришёл»), пригласившему +BONUS баллов и сообщение в бот — один раз.

Хранение в Redis (db 6, как язык) — схему БД не трогаем:
  ref:by:<tg друга>      = tg пригласившего
  ref:list:<tg приглас.>  = множество tg приглашённых
  ref:done:<tg друга>    = 1, бонус уже выдан
"""
import logging
from html import escape

from django.db.models import F

log = logging.getLogger(__name__)
BONUS = 5


def _r():
    from tgbot.services.lang import _sclient
    return _sclient()


def link(bot_username: str, tg_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{tg_id}"


def remember(new_tg_id: int, inviter_tg_id: int) -> bool:
    if not new_tg_id or not inviter_tg_id or new_tg_id == inviter_tg_id:
        return False
    try:
        r = _r()
        if r.set(f"ref:by:{new_tg_id}", inviter_tg_id, nx=True):
            r.sadd(f"ref:list:{inviter_tg_id}", new_tg_id)
            return True
    except Exception as e:
        log.warning("referral remember: %s", e)
    return False


def stats(tg_id: int) -> dict:
    try:
        r = _r()
        invited = [int(x) for x in r.smembers(f"ref:list:{tg_id}")]
        if not invited:
            return {"invited": 0, "joined": 0, "bonus": BONUS}
        pipe = r.pipeline()
        for x in invited:
            pipe.exists(f"ref:done:{x}")
        joined = sum(1 for v in pipe.execute() if v)
        return {"invited": len(invited), "joined": joined, "bonus": BONUS}
    except Exception:
        return {"invited": 0, "joined": 0, "bonus": BONUS}


def on_attended(user):
    """Вызывается, когда у человека участие стало «пришёл» (ProjectParticipation.save)."""
    if not user or not user.tg_id:
        return
    try:
        r = _r()
        inviter_tg = r.get(f"ref:by:{user.tg_id}")
        if not inviter_tg or not r.set(f"ref:done:{user.tg_id}", 1, nx=True):
            return
    except Exception as e:
        log.warning("referral on_attended: %s", e)
        return
    from .models import TGUser
    inviter = TGUser.objects.filter(tg_id=int(inviter_tg)).first()
    if not inviter:
        return
    TGUser.objects.filter(pk=inviter.pk).update(balance=F('balance') + BONUS)
    inviter.refresh_from_db(fields=['balance'])
    try:
        from tgbot.i18n import t as bot_t
        from tgbot.services.lang import lang_of_sync
        from .telegram import send_in_background
        send_in_background([(inviter.tg_id, bot_t("ref_bonus", lang_of_sync(inviter.tg_id), name=escape(user.fullname or "—"),
                                                  bonus=BONUS, balance=inviter.balance))])
    except Exception as e:
        log.warning("referral notify: %s", e)
