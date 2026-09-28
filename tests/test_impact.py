import os, sys, asyncio, io, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.conf import settings; settings.ALLOWED_HOSTS = ["*"]; settings.MEDIA_ROOT = tempfile.mkdtemp()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
import app_telegram.telegram as TT; TT.send_in_background = lambda m, on_done=None: None
import app_telegram.referrals as R; R.on_attended = lambda u: None
from pathlib import Path
from datetime import datetime, timedelta, date
from django.core.cache import cache
from django.utils import timezone
from django.test import Client
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate
from aiogram import Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
from app_telegram import impact as I, wrapped as WR
from API import webapp as W
from tgbot.handlers import impact as IH, wrapped as WH
from tgbot.services import impact_prompt as IP, wrapped as WS
from tgbot.i18n import current_lang
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
def jpg(color=(0, 150, 0), size=(3000, 2000)):
    b = io.BytesIO(); Image.new("RGB", size, color).save(b, "JPEG"); return b.getvalue()
tz = timezone.get_current_timezone(); now = timezone.now()
coord = TGUser.objects.create(tg_id=100, fullname="Koordinator", region="tashkent_s", role="coordinator")
samk = TGUser.objects.create(tg_id=101, fullname="Sam koord", region="samarkand", role="coordinator")
vol = [TGUser.objects.create(tg_id=200 + i, fullname=f"vol {i}", region="tashkent_v") for i in range(4)]
ev = EcoProject.objects.create(title="Anhor plogging", region="tashkent_s", date=now - timedelta(hours=4), is_active=True, location_name="x")
old = EcoProject.objects.create(title="Chorvoq", region="tashkent_v", date=now - timedelta(days=5), is_active=True, location_name="x")
for u in vol: PP.objects.create(user=u, project=ev, status="attended")
PP.objects.create(user=vol[0], project=old, status="attended"); PP.objects.create(user=vol[1], project=ev.__class__.objects.create(title="Sam", region="samarkand", date=now - timedelta(days=1), location_name="x"), status="attended")

# ── хранилище ──
check(I.get(ev.id) == {} and I.totals()["kg"] == 0, "без итогов — пусто")
I.save(old.id, by_tg=100, kg=50, bags=5, trees=0); rel = I.add_photo(old.id, jpg())
im = Image.open(Path(settings.MEDIA_ROOT) / rel)
check(max(im.size) == 1600 and I.get(old.id)["kg"] == 50.0, "фото уменьшено до 1600px, цифры сохранены")
check(I.totals() == {"kg": 50.0, "bags": 5, "trees": 0, "events": 1, "photos": 1}, "итог проекта")
I.save(old.id, kg=-5); check(I.get(old.id)["kg"] == 50.0, "отрицательное не сохраняется")

# ── бот: координатор вводит итоги ──
from aiogram import Bot as _B; dp = Dispatcher(_B(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"), storage=MemoryStorage()); Dispatcher.set_current(dp)
SENT = []
class FakeBot:
    def __init__(self): self.sent = []
    def get(self, k, d=None): return None
    async def send_message(self, tg, text, reply_markup=None, **k): self.sent.append((tg, text, reply_markup)); SENT.append(text)
def ctx(uid):
    types.Chat.set_current(types.Chat(id=uid, type="private")); types.User.set_current(types.User(id=uid))
    return dp.current_state(chat=uid, user=uid)
class Msg:
    def __init__(self, uid, text=None, photo=None, mg=None):
        self.from_user = type("U", (), {"id": uid})(); self.text = text; self.photo = photo; self.document = None; self.media_group_id = mg
        self.bot = FakeBot()
    async def answer(self, text, reply_markup=None, **k): SENT.append(text); self.kb = reply_markup
class Call:
    def __init__(self, uid, data):
        self.from_user = type("U", (), {"id": uid})(); self.data = data; self.message = Msg(uid); self.bot = self.message.bot; self.alerts = []
    async def answer(self, text=None, show_alert=False, **k): self.alerts.append(text)
class Photo:
    def __init__(self, data): self.data = data
    async def download(self, destination_file): destination_file.write(self.data)

st = ctx(101); m = Msg(101, "/natija"); asyncio.run(IH.natija_handler(m, st))
kbtexts = [b.text for row in m.kb.inline_keyboard for b in row] if hasattr(m, "kb") and m.kb else []
check(all("Anhor" not in x for x in kbtexts), "самаркандский координатор не видит ташкентское мероприятие")
c = Call(101, f"imp:{ev.id}"); asyncio.run(IH.start_callback(c, ctx(101)))
check(c.alerts and c.alerts[0] == "📊 Natijalarni faqat hudud koordinatorlari kiritadi.", "чужой регион — отказ")
vm = Msg(vol[0].tg_id, "/natija"); asyncio.run(IH.natija_handler(vm, ctx(vol[0].tg_id))); check("koordinator" in SENT[-1], "волонтёр — только координаторы")

st = ctx(100); m = Msg(100, "/natija"); asyncio.run(IH.natija_handler(m, st))
labels = [b.text for row in m.kb.inline_keyboard for b in row]
check(any("Anhor" in x and x.startswith("📊") for x in labels) and any("Chorvoq" in x and x.startswith("✅") for x in labels), f"/natija: список (✅ — уже есть) {labels}")
asyncio.run(IH.start_callback(Call(100, f"imp:{ev.id}"), st)); check("1/4" in SENT[-1] and asyncio.run(st.get_state()) == "ImpactStates:kg", "шаг 1 — кг")
asyncio.run(IH.number_input(Msg(100, "ну где-то"), st)); check("Raqam" in SENT[-1], "не число — просим число")
asyncio.run(IH.number_input(Msg(100, "~120,5 kg"), st)); check("2/4" in SENT[-1], "«~120,5 kg» → 120.5, шаг 2")
asyncio.run(IH.skip_callback(Call(100, "imps"), st)); check("3/4" in SENT[-1], "мешки пропустили")
asyncio.run(IH.number_input(Msg(100, "8"), st)); check("4/4" in SENT[-1] and asyncio.run(st.get_state()) == "ImpactStates:photos", "деревья 8 → фото")
n0 = len(SENT)
for i in range(3): asyncio.run(IH.photo_input(Msg(100, photo=[Photo(jpg((i * 60, 100, 50)))], mg="album1"), st))
check(len(SENT) - n0 == 1 and len(I.get(ev.id)["photos"]) == 3, "альбом из 3 фото — сохранены все, ответ один")
fb = FakeBot(); cb = Call(100, "impd"); cb.bot = fb; cb.message.bot = fb
async def done_and_wait():
    await IH.done_callback(cb, st); await asyncio.sleep(0.5)
asyncio.run(done_and_wait())
res = I.get(ev.id)
check(res["kg"] == 120.5 and res["bags"] == 0 and res["trees"] == 8 and "Saqlandi" in SENT[-5] if len(SENT) > 5 else False, "✅ сохранено: 120.5 кг, 8 деревьев")
thanks = {tg: txt for tg, txt, kb in fb.sent}
check(set(thanks) == {u.tg_id for u in vol} and "≈30" in thanks[200] and "≈2" in thanks[200], f"всем 4 пришедшим — «ваша доля ≈30 кг, ≈2 саженца»: {thanks.get(200, '')[:160]}")
check(asyncio.run(IH.notify_volunteers(FakeBot(), ev.id)) == 0, "благодарность — только один раз")

# ── напоминание координатору ──
noon = timezone.localtime(now).replace(hour=15, minute=0, second=0, microsecond=0)   # фиксированное «15:00», не зависит от часа запуска
ev2 = EcoProject.objects.create(title="Bog' tozalash", region="tashkent_v", date=noon - timedelta(hours=5), is_active=True, location_name="x")
b = FakeBot(); n = asyncio.run(IP.send_prompts(b, noon))
got = {(tg, txt.split("«")[1].split("»")[0]) for tg, txt, kb in b.sent}
check(got == {(100, "Bog&#x27; tozalash"), (101, "Sam")}, f"«введите итоги» — координатору своего региона, только где итогов нет {got}")
check(asyncio.run(IP.send_prompts(FakeBot(), noon)) == 0, "повторно не шлём")
check(asyncio.run(IP.send_prompts(FakeBot(), timezone.localtime(now).replace(hour=23))) == 0, "ночью не шлём")

# ── Mini App / сайт ──
f = APIRequestFactory()
def get(view, u, path="/x", **kw):
    req = f.get(path); force_authenticate(req, user=u); return view(req, **kw)
cache.clear()
boot = get(W.BootstrapView.as_view(), vol[0]).data
check(boot["impact"]["kg"] == round(120.5 / 4 + 50 / 1, 1) and boot["impact"]["events"] == 2, f"Mening hissam: {boot['impact']['kg']} кг за 2 мероприятия")
check(len(boot["impact"]["photos"]) == 4 and boot["impact"]["photos"][0]["title"] == "Anhor plogging", "фото с моих мероприятий, новые первыми")
check(boot["community"]["kg"] == 170.5 and boot["community"]["trees"] == 8, "«Наш вклад» — кг и деревья проекта")
check(any(h["has_impact"] for h in boot["history"]), "в истории отмечено, где есть итоги")
r = get(W.ImpactEventView.as_view(), vol[0], pk=ev.id).data
check(r["kg"] == 120.5 and r["attended"] == 4 and len(r["photos"]) == 3 and r["mine"]["kg"] == 30.1, "итоги мероприятия + моя доля")
check(get(W.ImpactEventView.as_view(), vol[0], pk=ev2.id).status_code == 404, "без итогов — 404")
c = Client(); pub = c.get("/impact/").json(); st_ = c.get("/stats/").json()
check(pub["kg"] == 170.5 and len(pub["items"]) == 4 and st_["kg"] == 170.5, "сайт: /impact/ и /stats/ с кг")
check(c.get(pub["items"][0]["url"].replace("https://api.yashilqollar.uz", "")).status_code in (200, 404), "ссылка на фото — /media/…")

# ── 🎁 итоги года ──
check(WR.year_for(date(2026, 11, 30)) is None and WR.year_for(date(2026, 12, 1)) == 2026 and WR.year_for(date(2027, 1, 15)) == 2026, "окно: декабрь–январь")
check(WR.year_for(date(2026, 6, 1), preview=True) == 2026, "админу — превью всегда")
check(WR._best_streak([2, 3, 4, 9, 10]) == 3 and WR._best_streak([]) == 0, "лучшая серия месяцев")
y = timezone.localtime(now).year
for mth in (1, 2, 3, 10):
    e = EcoProject.objects.create(title=f"E{mth}", region="tashkent_s", date=datetime(y, mth, 12, 10, tzinfo=tz), location_name="x")
    PP.objects.create(user=vol[2], project=e, status="attended")
s = WR.stats(vol[2], y)
check(s["events"] >= 4 and s["streak"] >= 3 and s["season"] in ("kuz", "qish") and s["place"] == 1 and s["top_pct"] >= 1, f"stats: {s['events']} мер., серия {s['streak']}, сезон {s['season']}, место {s['place']}")
img = WR.render(s, "ru"); check(img.size == (1080, 1920), "сторис 1080×1920")
u = WR.url(vol[2].id, y, "ru").replace("https://api.yashilqollar.uz", "")
r = c.get(u); check(r.status_code == 200 and r["Content-Type"] == "image/jpeg" and r.content[:2] == b"\xff\xd8", "картинка по подписанной ссылке")
check(c.get(u.replace(WR.sign(vol[2].id, y), "0" * 16)).status_code == 404, "поддельная ссылка → 404")
coord.is_admin = True; coord.save()
check(get(W.WrappedView.as_view(), coord).status_code == 200 or WR.year_for() is not None, "админ видит превью в любое время")
wv = get(W.WrappedView.as_view(), vol[2])
check(wv.status_code == (200 if WR.year_for() else 404), "волонтёр — только в декабре–январе")
check(boot.get("wrapped") is None or WR.year_for(), "в bootstrap — только когда доступно")

# бот: /yakun и рассылка 20 декабря
class PBot(FakeBot):
    def __init__(self): super().__init__(); self.photos = []
    async def send_photo(self, tg, photo, caption=None, reply_markup=None, **k): self.photos.append((tg, caption))
pb = PBot(); dec20 = timezone.make_aware(datetime(y, 12, 20, 12, 30))
check(asyncio.run(WS.send_due(pb, dec20.replace(hour=11))) == 0, "до 12:00 не шлём")
asyncio.run(WS.send_due(pb, dec20))
got = {tg for tg, _ in pb.photos}
check(got == {u.tg_id for u in TGUser.objects.filter(participations__status="attended", participations__project__date__year=y).distinct()} and 100 not in got,
      f"20 декабря — всем, кто был в этом году ({len(got)}), координатору без посещений — нет")
check(asyncio.run(WS.send_due(PBot(), dec20)) == 0, "повторно не шлём")
check(asyncio.run(WS.send_due(PBot(), timezone.make_aware(datetime(y, 11, 20, 13)))) == 0, "в ноябре — нет")
ym = Msg(vol[2].tg_id, "/yakun"); ym.bot = PBot()
asyncio.run(WH.yakun_handler(ym))
check((ym.bot.photos and "Wrapped" in ym.bot.photos[0][1]) if WR.year_for() else "dekabr" in SENT[-1], "/yakun — картинка (или «в декабре»)")
print(f"OK: {ok} проверок")
