"""
🚨 Уведомления об ошибках в Telegram — бот и сайт пишут сюда сами, когда что-то сломалось.

Куда: ALERT_CHAT_ID из .env (если нет — BACKUP_CHAT_ID, та же закрытая группа, куда идут бэкапы).
Как подключено:
  • бот — bot.py: логгер ERROR + errors_handler aiogram (ошибка в любом хендлере);
  • сайт/API — dj_ac/settings.py: LOGGING «django.request» (ответы 500);
  • «упал целиком» — scripts/healthcheck.sh по cron (процесс, который умер, сам сообщить не может).
Анти-спам: одинаковая ошибка — не чаще раза в REPEAT_GAP c; всего — не больше HOURLY_MAX сообщений в час.
Отправка в отдельном потоке: медленный Telegram никогда не тормозит бота или сайт.
"""
import hashlib
import json
import logging
import os
import socket
import threading
import time
import traceback
import urllib.request

REPEAT_GAP = int(os.environ.get("ALERT_REPEAT_GAP", "900"))
HOURLY_MAX = int(os.environ.get("ALERT_HOURLY_MAX", "20"))

_lock = threading.Lock()
_seen: dict[str, float] = {}
_sent: list[float] = []


def _target() -> tuple[str, str]:
    return (os.environ.get("BOT_TOKEN", "").strip(),
            (os.environ.get("ALERT_CHAT_ID") or os.environ.get("BACKUP_CHAT_ID") or "").strip())


def _post(token: str, chat: str, text: str):
    try:
        data = json.dumps({"chat_id": chat, "text": text[:4000], "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass                                    # уведомление не дошло — молча; логи остаются в docker logs


def allow(key: str, now: float | None = None) -> bool:
    """Анти-спам: та же ошибка не чаще раза в REPEAT_GAP, всего ≤ HOURLY_MAX в час."""
    now = now or time.time()
    with _lock:
        if now - _seen.get(key, 0) < REPEAT_GAP:
            return False
        _sent[:] = [t for t in _sent if now - t < 3600]
        if len(_sent) >= HOURLY_MAX:
            return False
        _seen[key] = now
        _sent.append(now)
        return True


def send(text: str, key: str | None = None, sync: bool = False) -> bool:
    token, chat = _target()
    if not token or not chat:
        return False
    if not allow(key or hashlib.sha1(text.encode()).hexdigest()):
        return False
    if sync:
        _post(token, chat, text)
    else:
        threading.Thread(target=_post, args=(token, chat, text), daemon=True).start()
    return True


class TelegramAlertHandler(logging.Handler):
    """ERROR и выше → короткое сообщение в Telegram: где, что, хвост трассировки."""

    def __init__(self, service: str):
        super().__init__(level=logging.ERROR)
        self.service = service

    def emit(self, record: logging.LogRecord):
        try:
            msg = record.getMessage()
            where = "/".join(record.pathname.replace("\\", "/").split("/")[-2:]) + f":{record.lineno}"
            tb, etype = "", ""
            if record.exc_info and record.exc_info[1] is not None:
                etype = type(record.exc_info[1]).__name__
                tb = "".join(traceback.format_exception(*record.exc_info))[-1500:]
            # ключ анти-спама: тип ошибки + место, без меняющихся деталей (id, время)
            key = f"{self.service}|{etype or msg[:80]}|{where}"
            text = (f"🚨 {self.service} · {socket.gethostname()}\n"
                    f"{time.strftime('%d.%m %H:%M:%S')} · {record.name}\n"
                    f"📍 {where}\n\n{msg[:800]}" + (f"\n\n{tb}" if tb else ""))
            send(text, key=key)
        except Exception:
            pass                                # обработчик логов никогда не должен ронять приложение
