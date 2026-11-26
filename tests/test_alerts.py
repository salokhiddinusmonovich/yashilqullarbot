"""🚨 Уведомления об ошибках: анти-спам, формат, Django 500 → Telegram, сторож healthcheck.sh."""
import os, sys, logging, subprocess, tempfile, shutil, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"
import django; django.setup()
from app_telegram import alerts as A
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)

SENT = []
REAL_POST = A._post
A._post = lambda token, chat, text: SENT.append((token, chat, text))
os.environ["BOT_TOKEN"], os.environ["BACKUP_CHAT_ID"] = "123:ABC", "-100777"
os.environ.pop("ALERT_CHAT_ID", None)

# анти-спам
A._seen.clear(); A._sent.clear()
t0 = 1_000_000.0
check(A.allow("x", t0) and not A.allow("x", t0 + 60), "та же ошибка через минуту — не повторяем")
check(A.allow("x", t0 + A.REPEAT_GAP + 1), f"через {A.REPEAT_GAP // 60} мин — снова можно")
A._seen.clear(); A._sent.clear()
check(sum(A.allow(f"k{i}", t0) for i in range(A.HOURLY_MAX + 5)) == A.HOURLY_MAX, f"не больше {A.HOURLY_MAX} сообщений в час")
A._seen.clear(); A._sent.clear()

# обработчик логов
log = logging.getLogger("tgbot.handlers.demo")
h = A.TelegramAlertHandler("bot"); log.addHandler(h)
def boom(uid):
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("spot card for user %s", uid)    # одна и та же строка кода, разные данные
boom(1); time.sleep(0.3)
check(SENT and SENT[-1][1] == "-100777" and "🚨 bot" in SENT[-1][2] and "ZeroDivisionError" in SENT[-1][2] and "test_alerts.py" in SENT[-1][2],
      "ошибка с трассировкой → в чат бэкапов (BACKUP_CHAT_ID), видно где и что")
n = len(SENT); boom(2); boom(3); time.sleep(0.2)
check(len(SENT) == n, "та же ошибка в том же месте (у других людей) — не дублируем")
log.warning("просто предупреждение"); time.sleep(0.2)
check(len(SENT) == n, "WARNING не отправляем — только ошибки")
os.environ["ALERT_CHAT_ID"] = "-100999"; A._seen.clear()
log.error("другая ошибка"); time.sleep(0.2)
check(SENT[-1][1] == "-100999", "ALERT_CHAT_ID важнее BACKUP_CHAT_ID")
os.environ.pop("ALERT_CHAT_ID"); token = os.environ.pop("BOT_TOKEN"); A._seen.clear(); n = len(SENT)
log.error("без токена"); time.sleep(0.2)
check(len(SENT) == n, "нет BOT_TOKEN — молча ничего не шлём (и не падаем)")
os.environ["BOT_TOKEN"] = token
log.removeHandler(h)
import urllib.request as UR
real_open = UR.urlopen
UR.urlopen = lambda *a, **k: (_ for _ in ()).throw(OSError("network down"))   # Telegram недоступен
A._post = REAL_POST
try:
    A.send("x", key="boom", sync=True); crashed = False
except Exception:
    crashed = True
UR.urlopen = real_open
A._post = lambda token, chat, text: SENT.append((token, chat, text))
check(True, "отправка не дошла — приложение не падает") if not crashed else check(False, "упало")

# Django: 500 → Telegram
from django.conf import settings as S
import logging.config
logging.config.dictConfig(S.LOGGING)
hs = logging.getLogger("django.request").handlers
check(any(isinstance(x, A.TelegramAlertHandler) and x.service == "web" for x in hs), "сайт: ошибки 500 (django.request) → Telegram")

# сторож healthcheck.sh — с подменёнными docker compose и curl
repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp(); os.makedirs(f"{tmp}/scripts")
shutil.copy(f"{repo}/scripts/healthcheck.sh", f"{tmp}/scripts/healthcheck.sh")
open(f"{tmp}/.env", "w").write("BOT_TOKEN=123:ABC\nBACKUP_CHAT_ID=-100777\n")
open(f"{tmp}/dc", "w").write(f'#!/bin/bash\nif [ "$1" = ps ]; then cat {tmp}/states; else echo "$@" >> {tmp}/dc.log; fi\n')
open(f"{tmp}/curl", "w").write(f'#!/bin/bash\nfor a in "$@"; do case "$a" in *api.telegram.org*) printf "%s\\n" "$@" >> {tmp}/tg.log; exit 0;; esac; done\ncat {tmp}/http\n')
os.chmod(f"{tmp}/dc", 0o755); os.chmod(f"{tmp}/curl", 0o755)
def run(states, http="200"):
    open(f"{tmp}/states", "w").write("".join(f"{s} {st}\n" for s, st in states.items())); open(f"{tmp}/http", "w").write(http)
    env = dict(os.environ, DC=f"{tmp}/dc", CURL=f"{tmp}/curl", DISK_WARN="101")
    return subprocess.run(["bash", f"{tmp}/scripts/healthcheck.sh"], env=env, capture_output=True, text=True).returncode
def tg(): return open(f"{tmp}/tg.log").read() if os.path.exists(f"{tmp}/tg.log") else ""
good = {"db": "running", "redis": "running", "web": "running", "bot": "running"}
check(run(good) == 0 and tg() == "", "всё работает — тишина")
check(run({**good, "bot": "exited"}) == 1 and "❌" in tg() and "bot: exited" in tg(), "бот упал → «❌ … bot: exited»")
check("up -d" in open(f"{tmp}/dc.log").read(), "и сторож пробует поднять (docker compose up -d)")
before = tg(); run({**good, "bot": "exited"})
check(tg() == before, "через 5 минут то же самое — не спамим")
run({**good, "bot": "exited"}, http="000")
check(tg().count("❌") == 2 and "не отвечает" in tg(), "добавилась новая проблема (сайт не отвечает) — сообщаем")
run(good)
check("✅" in tg(), "всё поднялось → «✅ снова работает»")
before = tg(); run(good)
check(tg() == before, "дальше всё хорошо — тишина")
# только диск — подсказка «освободить место», ничего не перезапускаем
open(f"{tmp}/dc.log", "w").close()
env_disk = dict(os.environ, DC=f"{tmp}/dc", CURL=f"{tmp}/curl", DISK_WARN="0")
open(f"{tmp}/states", "w").write("".join(f"{s} {st}\n" for s, st in good.items())); open(f"{tmp}/http", "w").write("200")
subprocess.run(["bash", f"{tmp}/scripts/healthcheck.sh"], env=env_disk, capture_output=True)
check("диск заполнен" in tg() and "prune" in tg().split("диск заполнен")[-1] and open(f"{tmp}/dc.log").read() == "",
      "забит только диск → подсказка как освободить место, сервисы не перезапускаем")
run(good)
del good["bot"]; run(good)
check("нет контейнера" in tg(), "контейнер бота пропал совсем (как было) → «bot: нет контейнера»")
shutil.rmtree(tmp)
print(f"OK: {ok} проверок")
