import os, sys, io, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"
import django; django.setup()
from django.conf import settings; settings.ALLOWED_HOSTS = ["*"]; settings.MEDIA_ROOT = tempfile.mkdtemp()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
from pathlib import Path
from datetime import datetime
from django.utils import timezone
from django.test import Client
from django.contrib.auth.models import User
from PIL import Image
from app_telegram import certificates as C
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
C.CUSTOM = Path(settings.MEDIA_ROOT) / "certificates"; C.DESIGNS = C.CUSTOM / "designs"
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
def png(color):
    b = io.BytesIO(); Image.new("RGB", (1754, 1240), color).save(b, "PNG"); b.seek(0); b.name = "x.png"; return b
tz = timezone.get_current_timezone()
def ev(title, m): return EcoProject.objects.create(title=title, region="tashkent_s", date=datetime(2026, m, 10, 10, tzinfo=tz), is_active=True, location_name="x")
u = TGUser.objects.create(tg_id=1, fullname="aziza rahimova")
aut, summ, win, nav = ev("Kuzgi plogging", 10), ev("Yozgi subbotnik", 7), ev("Qishki aksiya", 1), ev("Navro'z bayrami", 3)

# старый единственный шаблон переносится в «Kuz»
C.CUSTOM.mkdir(parents=True); Image.new("RGB", (1754, 1240), (200, 0, 0)).save(C.CUSTOM / "template.png")
(C.CUSTOM / "layout.json").write_text('{"name_y": 640}')
ds = {d["slug"]: d for d in C.designs()}
check(C.has_template("kuz") and not (C.CUSTOM / "template.png").exists() and C.layout("kuz")["name_y"] == 640, "старый шаблон и координаты → 🍂 Kuz")
check(list(ds)[:4] == ["kuz", "qish", "bahor", "yoz"] and all(ds[k]["ready"] for k in ("kuz", "qish", "bahor", "yoz")) and not ds["qish"]["custom_png"], "4 сезона, у всех есть встроенный дизайн")
check(C.template_path("qish").name == "qish.png" and C.layout("qish")["name_color"] == "#2F6690" and C.layout("qish")["body_show"], "❄️ Qish без PNG → встроенный зимний (свои цвета, абзац)")
(C.DESIGNS / "bahor").mkdir(parents=True, exist_ok=True); (C.DESIGNS / "bahor" / "layout.json").write_text('{"name_y": 111}')
check(C.layout("bahor")["name_y"] == 652, "старые координаты из админки не ломают новый встроенный дизайн")
C.save_layout({"name_y": 660}, "bahor"); check(C.layout("bahor")["name_y"] == 660, "правки для нового встроенного — применяются")
C.delete_design("bahor")

check(C.design_for(aut) == "kuz" and C.design_for(summ) == "yoz" and C.design_for(win) == "qish" and C.design_for(nav) == "bahor", "каждый сезон — свой встроенный дизайн")
C.save_template(png((255, 220, 0)), "yoz")
check(C.design_for(summ) == "yoz" and C.design_for(aut) == "kuz", "загрузили ☀️ Yoz → июльское мероприятие летнее, октябрьское осталось осенним")
pp = PP.objects.create(user=u, project=summ, status="attended")
check(C.render_for(pp).getpixel((10, 10)) == (255, 220, 0), "летний сертификат рисуется на летнем фоне")
pa = PP.objects.create(user=u, project=aut, status="attended")
check(C.render_for(pa).getpixel((10, 10)) == (200, 0, 0), "осенний — на осеннем (старое не изменилось)")

slug = C.create_design("Navro'z", "🌷")
C.save_template(png((0, 150, 0)), slug); C.save_meta(slug, months=[], events=[nav.id])
check(C.design_for(nav) == slug and C.design_for(aut) == "kuz", "особый дизайн «Navro'z» — только для своего мероприятия")
C.save_layout({"event_show": True, "event_y": 300, "event_size": 40}, slug)
img_off = C.render("Aziza", "01.01.2026", "YQ-1", slug="kuz", event_title="Navro'z bayrami")
img_on = C.render("Aziza", "01.01.2026", "YQ-1", slug=slug, event_title="Navro'z bayrami")
dark = lambda im: sum(1 for x in range(300, 830, 3) for y in range(270, 310, 3) if sum(im.getpixel((x, y))) < 200)
check(dark(img_on) > 20, "название мероприятия пишется, когда включено")

# админка
User.objects.create_superuser("adm", "a@a.uz", "pw"); c = Client(); c.login(username="adm", password="pw")
url = "/admin/app_telegram/projectparticipation/certificate/"
r = c.get(url + "?d=yoz"); html = r.content.decode()
check(r.status_code == 200 and "Yoz" in html and "Navro" in html and "cert-img" in html, "страница: вкладки сезонов и своих дизайнов")
check(c.get(url + "?d=yoz&preview=1&name_y=500").status_code == 200, "предпросмотр по дизайну")
c.post(url, {"d": "qish", "act": "save", "template": png((0, 0, 255)), "months": ["12", "1", "2"], "name_y": "620", "event_show": ""})
check(C.design_for(win) == "qish" and C.layout("qish")["name_y"] == 620, "загрузка ❄️ Qish через админку → январское мероприятие зимнее")
c.post(url, {"d": "yoz", "act": "save", "months": ["6", "7"], "events": ""})
check(C.meta("yoz")["months"] == [6, 7], "месяцы сезона меняются")
r = c.post(url, {"act": "new", "name": "Kitob kuni", "emoji": "📚"})
check(r.status_code == 302 and "kitob-kuni" in r["Location"], "➕ новый дизайн")
c.post(url, {"d": "qish", "act": "reset"}); check(C.design_for(win) == "qish" and C.template_path("qish").name == "qish.png", "↩ сброс ❄️ Qish → снова встроенный зимний")
c.post(url, {"d": slug, "act": "reset"}); check(slug not in [d["slug"] for d in C.designs()], "🗑 свой дизайн удалён")
print(f"OK: {ok} проверок")
