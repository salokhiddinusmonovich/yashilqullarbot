import os, sys, asyncio, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.conf import settings; settings.ALLOWED_HOSTS = ["*"]; settings.MEDIA_ROOT = tempfile.mkdtemp()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
import app_telegram.telegram as TT; TT.send_in_background = lambda m, on_done=None: None
from pathlib import Path
from datetime import datetime, timedelta
from django.utils import timezone
from django.test import Client
from rest_framework.test import APIRequestFactory, force_authenticate
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
from app_telegram import cv, certificates as C
C.CUSTOM = Path(settings.MEDIA_ROOT) / "certificates"; C.DESIGNS = C.CUSTOM / "designs"
from API import webapp as W
from tgbot.services import digest as D
from tgbot.handlers import certs as CH, digest as DH
from tgbot.i18n import current_lang
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
tz = timezone.get_current_timezone(); now = timezone.now()
u = TGUser.objects.create(tg_id=10, fullname="aziza rahimova", region="tashkent_s")
past = [EcoProject.objects.create(title=f"Tadbir {i}", region="tashkent_s", date=now - timedelta(days=30 * i + 1), is_active=True, location_name="x") for i in range(3)]
for e in past: PP.objects.create(user=u, project=e, status="attended")
# CV
pdf = cv.build(u, "ru"); check(pdf[:4] == b"%PDF" and len(pdf) > 10000, "CV: PDF собирается")
c = Client()
check(c.get(f"/c/cv/{u.id}-{cv.sign(u.id)}.pdf").status_code == 200 and c.get(f"/c/cv/{u.id}-{'0'*16}.pdf").status_code == 404, "CV: ссылка с подписью; поддельная → 404")
f = APIRequestFactory(); req = f.get("/x"); force_authenticate(req, user=u)
boot = W.BootstrapView.as_view()(req).data
check(boot["cv_url"].endswith(f"/c/cv/{u.id}-{cv.sign(u.id)}.pdf"), "Mini App получает ссылку на CV")
check(c.get(boot["history"][0]["cert"]["pdf"].replace("https://api.yashilqollar.uz", "")).status_code == 200, "сертификат по ссылке из Mini App открывается (после дизайнов)")
SENT = []
class Msg:
    from_user = type("U", (), {"id": 10})()
    async def answer(self, text, reply_markup=None, **k): SENT.append(("T", text, reply_markup))
    async def answer_document(self, doc, caption=None, **k): SENT.append(("D", doc.filename, caption))
asyncio.run(CH.cv_handler(Msg())); check(SENT[-1][0] == "D" and SENT[-1][1].startswith("Yashil_Qollar_CV_Aziza"), "/cv → PDF в бот")

# дайджест
monday = timezone.localtime(now) - timedelta(days=timezone.localtime(now).weekday()); monday = monday.replace(hour=10, minute=30)
e1 = EcoProject.objects.create(title="Daraxt ekish", region="tashkent_v", date=monday + timedelta(days=2), is_active=True, location_name="Chirchiq", max_participants=50)
e2 = EcoProject.objects.create(title="Plogging", region="tashkent_s", date=monday + timedelta(days=4), is_active=True, location_name="Anhor", max_participants=1)
e3 = EcoProject.objects.create(title="Samarqand aksiyasi", region="samarkand", date=monday + timedelta(days=3), is_active=True, location_name="R")
other = TGUser.objects.create(tg_id=11, fullname="Bek", region="tashkent_s"); PP.objects.create(user=other, project=e2, status="approved")
sam = TGUser.objects.create(tg_id=12, fullname="Sam", region="samarkand")
TGUser.objects.create(tg_id=13, fullname="NoRegion")
class Bot:
    def __init__(self): self.sent = []
    async def send_message(self, tg, text, reply_markup=None, **k): self.sent.append((tg, text, reply_markup))
bot = Bot()
check(asyncio.run(D.send_digest(bot, monday.replace(hour=9))) == 0, "в понедельник до 10:00 — не шлём")
asyncio.run(D.send_digest(bot, monday))
by = {tg: (txt, kb) for tg, txt, kb in bot.sent}
check(set(by) == {10, 11, 12}, f"получили: Азиза, Бек, Сэм (без региона — нет) → {sorted(by)}")
txt, kb = by[10]
check("Daraxt ekish" in txt and "Plogging" in txt and "Samarqand" not in txt, "Азизе — Ташкент город+область, без Самарканда")
check("navbatga" in txt and kb.inline_keyboard[0][0].callback_data == f"evreg:{e1.id}", "полное — «можно в очередь»; кнопки «✅ Записаться»")
check("Plogging" not in by[11][0], "Беку не предлагаем, куда он уже записан")
check(asyncio.run(D.send_digest(Bot(), monday)) == 0, "повторно на этой неделе не шлём")
class Call:
    data = "digest:off"; from_user = type("U", (), {"id": 12})(); message = Msg()
    async def answer(self, *a, **k): pass
asyncio.run(DH.digest_off(Call()))
L._async.srem  # noqa
asyncio.run(L._async.delete(f"digest:sent:{D.week_key(monday)}"))
b2 = Bot(); asyncio.run(D.send_digest(b2, monday)); check(12 not in {x[0] for x in b2.sent}, "«🔕 Отключить» — больше не шлём")
check(asyncio.run(D.send_digest(Bot(), monday.replace(hour=11) + timedelta(days=1))) == 0, "во вторник — нет")
print(f"OK: {ok} проверок")
