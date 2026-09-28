import os, sys, asyncio, io, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.conf import settings; settings.ALLOWED_HOSTS = ["*"]; settings.MEDIA_ROOT = tempfile.mkdtemp()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, tgbot.services.lang as L; L._sync = fakeredis.FakeRedis(decode_responses=True)
import app_telegram.referrals as R; R.on_attended = lambda u: None
from pathlib import Path
from datetime import datetime
from django.utils import timezone
from django.test import Client
from django.contrib.auth.models import User
from app_telegram import certificates as C
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
C.CUSTOM = Path(settings.MEDIA_ROOT) / "certificates"; C.DESIGNS = C.CUSTOM / "designs"
from tgbot.handlers import certs as CH
from tgbot.i18n import current_lang
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
tz = timezone.get_current_timezone()
u = TGUser.objects.create(tg_id=10, fullname="aziza rahimova", region="tashkent_s")
dates = [datetime(2025, 7, 5, 10, tzinfo=tz), datetime(2025, 10, 12, 10, tzinfo=tz), datetime(2025, 12, 20, 10, tzinfo=tz),
         datetime(2026, 1, 15, 10, tzinfo=tz), datetime(2026, 9, 27, 10, tzinfo=tz)]
pps = []
for i, d in enumerate(dates):
    e = EcoProject.objects.create(title=f"Tadbir {i}", region="tashkent_s", date=d, is_active=True, location_name="x")
    pps.append(PP.objects.create(user=u, project=e, status="attended"))
check([C.season_of(d)[1] for d in dates] == ["☀️ Yoz 2025", "🍂 Kuz 2025", "❄️ Qish 2025–26", "❄️ Qish 2025–26", "🍂 Kuz 2026"], "сезоны: декабрь и январь — одна зима «2025–26»")
check(C.season_of(dates[0], "ru")[1] == "☀️ Лето 2025", "подписи на языке человека")
img = C.render_for(pps[-1])
crop = img.crop((72, 100, 202, 230)).convert("L")
dark = sum(crop.histogram()[:120]) / (crop.width * crop.height)
check(dark > 0.25, "QR нарисован в левом верхнем углу")
import zxingcpp   # тот же, что бот использует для скриншотов (requirements.txt)
found = [r.text for r in zxingcpp.read_barcodes(img.crop((30, 60, 260, 280)))]
check(C.verify_url(pps[-1].id) in found, f"QR сканируется и ведёт на проверку ({found})")
c = Client()
r = c.get(C.verify_url(pps[-1].id).replace(C.PUBLIC_URL, ""))
html = r.content.decode()
check(r.status_code == 200 and "Haqiqiy sertifikat" in html and "Aziza Rahimova" in html and "Tadbir 4" in html and C.number_of(pps[-1]) in html, "QR → страница «✅ Haqiqiy sertifikat» с именем, мероприятием, №")
check(c.get(f"/c/v/{pps[-1].id}-0000000000").status_code == 404, "поддельная ссылка → «❌ не найден»")
pps[0].status = "approved"; pps[0].save()
check(c.get(C.verify_url(pps[0].id).replace(C.PUBLIC_URL, "")).status_code == 404, "отметку отменили → сертификат недействителен")
pps[0].status = "attended"; pps[0].save()
# бот: группы по сезонам
SENT = []
class Msg:
    from_user = type("U", (), {"id": 10})()
    async def answer(self, text, reply_markup=None, **k): SENT.append(reply_markup)
asyncio.run(CH.certs_handler(Msg()))
labels = [row[0].text for row in SENT[-1].inline_keyboard]
check(labels[0] == "— 🍂 Kuz 2026 —" and "— ❄️ Qish 2025–26 —" in labels and labels.count("— ❄️ Qish 2025–26 —") == 1 and labels[-2] == "— ☀️ Yoz 2025 —",
      f"/sertifikat: заголовки сезонов, новые сверху ({[l for l in labels if l.startswith('—')]})")
# админка: ZIP
User.objects.create_superuser("adm", "a@a.uz", "pw"); c.login(username="adm", password="pw")
ids = [p.project_id for p in pps[2:4]]
r = c.post("/admin/app_telegram/ecoproject/", {"action": "download_certificates_zip", "_selected_action": ids})
z = zipfile.ZipFile(io.BytesIO(r.content))
names = sorted(z.namelist())
check(r["Content-Type"] == "application/zip" and len(names) == 2 and names[0].startswith("2025-12-20 Tadbir 2/Aziza Rahimova (YQ-"), f"ZIP: папка на мероприятие, PDF внутри ({names[0]})")
print(f"OK: {ok} проверок")
