import os, sys, asyncio, io, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.conf import settings; settings.ALLOWED_HOSTS = ["*"]; settings.MEDIA_ROOT = tempfile.mkdtemp()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
import app_telegram.telegram as TT
BG = []; TT.send_in_background = lambda m, on_done=None: BG.extend(m)
import app_telegram.referrals as R; R.on_attended = lambda u: None
from datetime import timedelta
from django.utils import timezone
from django.test import Client
from django.contrib.auth.models import User
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate
from aiogram import Dispatcher, types, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
from app_telegram import spots as SP, impact as I
import app_telegram.admin as ADM; ADM.send_in_background = TT.send_in_background
from API import webapp as W
from tgbot.handlers import spots as SH, impact as IH
from tgbot.services import geo
from tgbot.i18n import current_lang
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
def jpg(color=(90, 120, 40)):
    b = io.BytesIO(); Image.new("RGB", (2000, 1500), color).save(b, "JPEG"); return b.getvalue()

GEO = {}
async def fake_reverse(lat, lon, lang="uz"): return GEO.get((round(lat, 2), round(lon, 2)))
geo.reverse = fake_reverse
GEO[(40.12, 67.84)] = {"country": "uz", "region": "jizzakh", "address": "Sharof Rashidov ko'chasi, Jizzax"}
GEO[(42.32, 69.6)] = {"country": "kz", "region": None, "address": "Shymkent"}

vol = TGUser.objects.create(tg_id=500, fullname="Aziza Rahimova", region="jizzakh", username="aziza")
coordJ = TGUser.objects.create(tg_id=501, fullname="Jizzax koord", region="jizzakh", role="coordinator")
coordS = TGUser.objects.create(tg_id=502, fullname="Samarqand koord", region="samarkand", role="coordinator")
admin = TGUser.objects.create(tg_id=503, fullname="Admin", region="tashkent_s", is_admin=True)
other = TGUser.objects.create(tg_id=504, fullname="Bek", region="jizzakh")
admin2 = TGUser.objects.create(tg_id=505, fullname="Admin2", region="samarkand", is_admin=True)
founder = TGUser.objects.create(tg_id=506, fullname="Founder", region="jizzakh", role="Founder")

bot = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw")
dp = Dispatcher(bot, storage=MemoryStorage()); Dispatcher.set_current(dp)
SENT = []
class FakeBot:
    def __init__(self): self.log = []
    def get(self, k, d=None): return None
    async def send_message(self, tg, text, reply_markup=None, **k): self.log.append(("T", tg, text, reply_markup))
    async def send_media_group(self, tg, media, **k): self.log.append(("G", tg, [m.media for m in media], None))
    async def send_photo(self, tg, photo, **k): self.log.append(("P", tg, photo, None))
    async def send_location(self, tg, lat, lon, **k): self.log.append(("L", tg, (lat, lon), None))
    async def download_file_by_id(self, fid, destination): destination.write(jpg())
FB = FakeBot()
def st(uid):
    types.Chat.set_current(types.Chat(id=uid, type="private")); types.User.set_current(types.User(id=uid))
    return dp.current_state(chat=uid, user=uid)
class Msg:
    def __init__(self, uid, text=None, photo=None, mg=None, location=None):
        self.from_user = type("U", (), {"id": uid})(); self.chat = type("C", (), {"id": uid})()
        self.text = text; self.photo = photo; self.document = None; self.media_group_id = mg
        self.location = location; self.venue = None; self.bot = FB; self.kb = None; self.html_text = "card"
    async def answer(self, text, reply_markup=None, **k): SENT.append((text, reply_markup)); self.kb = reply_markup
    async def edit_reply_markup(self, kb=None): self.kb = kb
    async def edit_text(self, text, reply_markup=None, **k): self.edited = (text, reply_markup)
    async def answer_photo(self, photo, caption=None, reply_markup=None, **k):
        SENT.append((caption, reply_markup)); self.kb = reply_markup; self.sent_photo = photo
        return type("M", (), {"photo": [type("P", (), {"file_id": "FID-card"})()]})()
    async def edit_media(self, media, reply_markup=None, **k):
        SENT.append((media.caption, reply_markup)); self.kb = reply_markup
        return type("M", (), {"photo": [type("P", (), {"file_id": "FID-card"})()]})()
    async def answer_location(self, lat, lon, **k): SENT.append((f"LOC {lat:.4f},{lon:.4f}", None))
    async def answer_media_group(self, media, **k): SENT.append((f"ALBUM {len(media)}", None))
    async def delete(self): self.deleted = True
class Call:
    def __init__(self, uid, data):
        self.from_user = type("U", (), {"id": uid})(); self.data = data; self.message = Msg(uid); self.bot = FB; self.message.bot = FB; self.alerts = []
    async def answer(self, text=None, show_alert=False, **k): self.alerts.append(text)
class Photo:
    def __init__(self, fid): self.file_id = fid
Loc = lambda lat, lon: type("L", (), {"latitude": lat, "longitude": lon})()
run = asyncio.run
def last(): return SENT[-1][0]
def btns(kb): return [b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data] if kb else []

# ── не зарегистрирован / начало ──
run(SH.spot_start(Msg(999), st(999))); check("ro'yxatdan" in last(), "без регистрации — «сначала зарегистрируйтесь»")
s = st(500); run(SH.spot_start(Msg(500), s)); check("1/6" in last() and run(s.get_state()) == "SpotStates:photos", "шаг 1 — фото")
c = Call(500, "spn"); run(SH.next_callback(c, s)); check(c.alerts and "1 ta rasm" in c.alerts[0], "без фото дальше нельзя")
n0 = len(SENT)
for i in range(3): run(SH.photo_input(Msg(500, photo=[Photo(f"fid{i}")], mg="alb1"), s))
check(len(SENT) - n0 == 1, "альбом из 3 фото — один ответ")
for i in range(4): run(SH.photo_input(Msg(500, photo=[Photo(f"x{i}")]), s))
check(run(L._async.llen("spot:draft:500")) == 5 and "5 ta" in last(), "больше 5 фото — не берём")
run(SH.next_callback(Call(500, "spn"), s)); check("2/6" in last() and run(s.get_state()) == "SpotStates:location", "шаг 2 — геолокация (кнопка)")
run(SH.location_input(Msg(500, location=Loc(42.32, 69.6)), s)); check("O'zbekiston" in last() and run(s.get_state()) == "SpotStates:location", "Шымкент (Казахстан) — не принимаем")
run(SH.location_input(Msg(500, location=Loc(40.12, 67.84)), s))
check("4/6" in last() and btns(SENT[-1][1])[0] == "sps:small", "Джизак — регион сам по карте, сразу «сколько мусора»")
for data in ("sps:large", "spk:household", "spa:easy"):
    run(SH.details_callback(Call(500, data), s))
check("✍️" in last() and run(s.get_state()) == "SpotStates:note", "размер/вид/доступ → комментарий")
run(SH.note_input(Msg(500, "Bozor orqasida, ariq bo'yida"), s))
check("Jizzax viloyati" in last() and "Sharof Rashidov" in last() and "Bozor orqasida" in last(), "подтверждение со всеми ответами")
FB.log.clear(); run(SH.send_callback(Call(500, "spok"), s)); run(asyncio.sleep(0))
async def settle(): await asyncio.sleep(0.3)
run(settle())
sp = SP.get(1)
check(sp and sp["status"] == "new" and sp["region"] == "jizzakh" and len(sp["photos"]) == 5 and sp["size"] == "large", "место #1 сохранено: 5 фото, Джизак")
check("#1" in last() and "+5" in last(), "автору: «спасибо, #1, +5 / +10»")

# уведомления модераторам — через notify_moderators (в тесте вызываем сами, create_task в другом loop)
fb = FakeBot(); run(SH.notify_moderators(fb, sp, [f"fid{i}" for i in range(3)], vol))
got = {tg for kind, tg, *_ in fb.log}
check(got == {503, 505}, f"пришло только тем, у кого is_admin (не координатору, не основателю без галочки): {sorted(got)}")
card = [x for x in fb.log if x[0] == "T" and x[1] == 503][0]
check("Aziza" in card[2] and "maps.google.com" in card[2] and btns(card[3]) == ["sm:a:1", "sm:r:1", "sm:e:1", "sm:d:1"], "карточка: автор, ссылки на карту, 4 кнопки")
check(any(x[0] == "G" for x in fb.log) and any(x[0] == "L" for x in fb.log), "альбом фото + точка на карте")

# ── модерация ──
for uid in (501, 506):
    c = Call(uid, "sm:a:1"); run(SH.mod_callback(c)); check(c.alerts and "adminlar" in c.alerts[0], f"{uid}: без галочки is_admin кнопки не работают (даже основатель)")
bal = TGUser.objects.get(id=vol.id).balance
FB.log.clear(); c = Call(503, "sm:a:1"); run(SH.mod_callback(c))
check(SP.get(1)["status"] == "accepted" and TGUser.objects.get(id=vol.id).balance == bal + 5, "✅ принято → автору +5")
check(any(x[1] == 500 and "qabul" in x[2] for x in FB.log if x[0] == "T"), "автору: «принято»")
check(btns(c.message.edited[1]) == ["sm:e:1", "sm:c:1"] and "Admin" in c.message.edited[0], "карточка обновилась: кто принял, дальше — 📅 / 🧹")
c = Call(505, "sm:a:1"); run(SH.mod_callback(c)); check(c.alerts and "Allaqachon" in c.alerts[0], "второй модератор — «уже принято»")
FB.log.clear(); c = Call(503, "sm:e:1"); run(SH.mod_callback(c))
sp = SP.get(1); ev = EcoProject.objects.get(id=sp["event_id"])
check(sp["status"] == "planned" and not ev.is_active and ev.region == "jizzakh" and ev.date.weekday() == 5 and "Sharof Rashidov" in ev.title, f"📅 черновик мероприятия (выкл., суббота): {ev.title}")
check("/admin/app_telegram/ecoproject/" in last() and TGUser.objects.get(id=vol.id).balance == bal + 5, "модератору — ссылка на черновик; баллы за «принято» не дважды")

# итоги мероприятия → место убрано, «до / после», +10
for u in (vol, other): PP.objects.create(user=u, project=ev, status="attended")
bal = TGUser.objects.get(id=vol.id).balance - 5   # за посещение свои баллы (сигнал)
I.save(ev.id, by_tg=501, kg=300); I.add_photo(ev.id, jpg((20, 200, 20)))
fb2 = FakeBot(); run(SH.notify_cleaned_by_event(fb2, ev.id))
sp = SP.get(1)
check(sp["status"] == "cleaned" and len(sp["after"]) == 1 and TGUser.objects.get(id=vol.id).balance == bal + 15, "итоги внесены → 🧹 убрано, фото «после», ещё +10")
g = [x for x in fb2.log if x[0] == "G"]
check(g and len(g[0][2]) == 2 and any("tozalandi" in x[2] for x in fb2.log if x[0] == "T"), "автору — альбом «до / после» и «место убрано»")

# ── второе место рядом → «это то же место?» ──
s2 = st(504); run(SH.spot_start(Msg(504), s2)); run(SH.photo_input(Msg(504, photo=[Photo("b1")]), s2)); run(SH.next_callback(Call(504, "spn"), s2))
SP.create(other, 40.1201, 67.8401, "jizzakh", "small", "plastic", "easy", "", "", [jpg()])  # #2 открыто рядом
run(SH.location_input(Msg(504, location=Loc(40.1202, 67.8402)), s2))
check(btns(SENT[-1][1]) == ["spd:2", "spnew"], "рядом уже есть открытое #2 — «это то же место?»")
run(SH.details_callback(Call(504, "spd:2"), s2)); check(SP.get(2)["confirms"] == 1 and run(s2.get_state()) is None, "«да» → подтверждение +1, без нового сообщения")

# регион, если карта не ответила
s3 = st(504); run(SH.spot_start(Msg(504), s3)); run(SH.photo_input(Msg(504, photo=[Photo("c1")]), s3)); run(SH.next_callback(Call(504, "spn"), s3))
run(SH.location_input(Msg(504, location=Loc(39.66, 66.95)), s3))
check(btns(SENT[-1][1]) == ["spr:samarkand", "spro"], "OpenStreetMap молчит → «Samarqand viloyati?» + «другой регион»")
run(SH.details_callback(Call(504, "spro"), s3)); check(len(btns(SENT[-1][1])) == 14, "список всех 14 регионов")
run(SH.details_callback(Call(504, "spx"), s3)) if False else run(SH.cancel_callback(Call(504, "spx"), s3))
check(run(s3.get_state()) is None and "Bekor" in last(), "✖️ отмена")

# лимит в день
for _ in range(5): SP.create(other, 41.0, 69.0, "tashkent_v", "small", "mixed", "easy", "", "", [jpg()])
run(SH.spot_start(Msg(504), st(504))); check("ertaga" in last().lower(), "больше 3 в день — «завтра»")

# ── Mini App / сайт ──
f = APIRequestFactory()
def get(view, u, **kw):
    req = f.get("/x"); force_authenticate(req, user=u); return view(req, **kw)
mine = get(W.SpotsView.as_view(), other).data["spots"]; pub = get(W.SpotsView.as_view(), coordS).data["spots"]
check({x["id"] for x in pub} == {1} and all(x["mine"] for x in mine if x["status"] == "new"), "карта: всем — только проверенные; свои — все (с «mine»)")
d = get(W.SpotView.as_view(), coordS, pk=1).data
check(d["status"] == "cleaned" and len(d["photos"]) == 5 and len(d["after"]) == 1 and d["event"]["id"] == ev.id, "место: фото, «после», мероприятие")
check(get(W.SpotView.as_view(), coordJ, pk=2).status_code == 404 and get(W.SpotView.as_view(), admin, pk=2).status_code == 200, "непроверенное — только автору и админам")
boot = get(W.BootstrapView.as_view(), other).data
check(boot["spots"] == {"open": 0, "cleaned": 1, "mine": 6}, f"bootstrap: {boot['spots']}")
cl = Client(); ps = cl.get("/spots/").json()
check([x["id"] for x in ps["spots"]] == [1] and "mine" not in ps["spots"][0] and ps["counts"]["cleaned"] == 1, "сайт /spots/: проверенные, без авторов")

# ── админка ──
User.objects.create_superuser("adm", "a@a.uz", "pw"); cl.login(username="adm", password="pw")
url = "/admin/app_telegram/projectparticipation/spots/"
r = cl.get(url + "?st=new"); html = r.content.decode()
check(r.status_code == 200 and "#2" in html and "sp-map" in html and "Bek" in html, "админка: карта и список новых")
BG.clear(); r = cl.post(url + "?st=new", {"id": 2, "act": "accepted"})
check(r.status_code == 302 and SP.get(2)["status"] == "accepted" and BG and BG[0][0] == 504 and "+5" in BG[0][1], "админка: «принять» → автору сообщение и +5")
r = cl.post(url, {"id": 3, "act": "event"}); check(r.status_code == 302 and "/ecoproject/" in r["Location"] and SP.get(3)["status"] == "planned", "админка: «📅 мероприятие» → на страницу черновика")
check(cl.get("/admin/").status_code == 200 and "spots/" in cl.get("/admin/").content.decode(), "ссылка на главной админки")

# ── 📍 из Mini App: фото по одному → сообщение ──
from django.core.files.uploadedfile import SimpleUploadedFile
import app_telegram.telegram as TT2
BOT_TASKS = []; TT2.run_with_bot_in_background = lambda fn: BOT_TASKS.append(fn)
fresh = TGUser.objects.create(tg_id=600, fullname="Madina", region="jizzakh")
def post(view, u, data, fmt="json", **kw):
    req = f.post("/x", data, format=fmt); force_authenticate(req, user=u); return view(req, **kw)
toks = [post(W.SpotPhotoView.as_view(), fresh, {"photo": SimpleUploadedFile("a.jpg", jpg((i * 40, 90, 60)), "image/jpeg")}, "multipart").data["token"] for i in range(2)]
check(all(len(t) == 16 for t in toks), "фото загружаются по одному → токены")
body = {"tokens": toks, "lat": 40.1203, "lon": 67.8403, "size": "medium", "kind": "plastic", "access": "easy", "note": "ariq"}
r = post(W.SpotsView.as_view(), fresh, body).data
check(r["result"] == "near" and r["spot"]["id"] == 2, "рядом открытое #2 → «это то же место?»")
check(post(W.SpotConfirmView.as_view(), fresh, {}, pk=2).data["confirms"] == 2, "«да» → подтверждение")
check(post(W.SpotsView.as_view(), fresh, {**body, "lat": 42.32, "lon": 69.6}).data["result"] == "not_uz", "Казахстан — нет")
r = post(W.SpotsView.as_view(), fresh, {**body, "force": True}).data
sp = SP.get(r["spot"]["id"])
check(r["result"] == "ok" and len(sp["photos"]) == 2 and sp["region"] == "jizzakh" and sp["uid"] == fresh.id, "«нет, другое место» → сохранено, 2 фото, Джизак")
check(post(W.SpotsView.as_view(), fresh, {**body, "tokens": toks, "force": True, "lat": 40.5, "lon": 68.0}).status_code == 400, "чужие/использованные токены не подходят")
fb3 = FakeBot(); run(BOT_TASKS[-1](fb3))
check({x[1] for x in fb3.log} == {503, 505} and any(x[0] == "G" for x in fb3.log), "модераторам — та же карточка с фото (файлами)")
det = get(W.SpotView.as_view(), fresh, pk=sp["id"]).data
check("/thumbs/900/" in det["photos"][0] and "/thumbs/240/" in det["photo"], "в Mini App — уменьшенные копии фото")

# ── 🗺 эко-карта в боте (текстовый режим) ──
SP.set_status(3, "planned"); ev3 = EcoProject.objects.get(id=SP.get(3)["event_id"]); ev3.is_active = True; ev3.save()
m = Msg(500, "📍 Iflos joy"); run(SH.spot_hub(m, st(500)))
hub = last(); hb = btns(m.kb)
check("Jizzax viloyati" in hub and "Tozalanishi kerak: <b>1</b>" in hub and "Tozalandi: <b>1</b>" in hub, f"меню: сводка по своему региону (Джизак): {hub[:120]!r}")
check(hb[:5] == ["sphn", "spv:d:r:0", "spv:p:r:0", "spv:c:r:0", "spv:m:a:0"] and "sph:a" in hb, "кнопки: сообщить / грязно / в планах / убрано / мои / вся страна")
c = Call(500, "sph:a"); run(SH.hub_callback(c, st(500)))
check("Butun O'zbekiston" in c.message.edited[0] and "Tadbir rejalashtirilgan: <b>1</b>" in c.message.edited[0], "«🌍 вся страна» — сводка по всему Узбекистану")
c = Call(500, "sphn"); run(SH.hub_callback(c, st(500))); check("1/6" in last(), "«📍 сообщить» из меню → шаги")
run(SH.cancel_callback(Call(500, "spx"), st(500)))
c = Call(500, "spv:d:r:0"); run(SH.view_callback(c))
cap, kb = SENT[-1]
check("#2" in cap and "Jizzax" in cap and "spc:2" in btns(kb) and "spl:2" in btns(kb) and any(b.url and "maps.google" in b.url for r in kb.inline_keyboard for b in r),
      "карточка «грязно»: фото, #2 Джизак, «всё ещё грязно», точка, Google Maps")
check("spv:" not in "".join(btns(kb)), "одна карточка — без ⬅️ ➡️")
check(isinstance(c.message.sent_photo, types.InputFile) and run(L._async.get(f"spot:fid:{SP.get(2)['photos'][0]}")) == "FID-card", "фото — уменьшенная копия файлом, file_id запомнили")
c = Call(500, "spv:d:r:0"); run(SH.view_callback(c)); check(c.message.sent_photo == "FID-card", "второй раз — по file_id, без загрузки")
c = Call(500, "spv:c:a:0"); run(SH.view_callback(c)); cap, kb = SENT[-1]
check("#1" in cap and "spba:1" in btns(kb) and "spc:1" not in btns(kb), "«убрано»: кнопка «до / после», без «всё ещё грязно»")
run(SH.before_after_callback(Call(500, "spba:1"))); check(last() == "ALBUM 2", "«до / после» — альбом")
c = Call(500, "spv:p:a:0"); run(SH.view_callback(c)); cap, kb = SENT[-1]
check("Tozalash" in cap and f"evreg:{ev3.id}" in btns(kb), "«в планах»: мероприятие и «✅ записаться» (evreg)")
run(SH.location_callback(Call(500, "spl:2"))); check(last().startswith("LOC 40.12"), "«📍 точка» — геолокация в чат")
c = Call(500, "spc:2"); run(SH.still_dirty_callback(c)); check(c.alerts[-1] and "Rahmat" in c.alerts[-1], "«👍 всё ещё грязно» → спасибо")
c = Call(504, "spc:3"); run(SH.still_dirty_callback(c)); check("sizning" in c.alerts[-1], "своё сообщение подтвердить нельзя")
c = Call(504, "spv:m:a:0"); run(SH.view_callback(c)); cap, kb = SENT[-1]
check("1 / " in "".join(b.text for r in kb.inline_keyboard for b in r) and "spv:m:a:1" in btns(kb), "«мои»: листание ⬅️ ➡️")
c = Call(504, "spv:m:a:1"); c.message.photo = [1]; run(SH.view_callback(c)); check("2 / " in "".join(b.text for r in c.message.kb.inline_keyboard for b in r), "➡️ меняет фото в той же карточке")
c = Call(500, "sph:r"); c.message.photo = [1]; run(SH.hub_callback(c, st(500))); check(getattr(c.message, "deleted", False) and "Iflos joylar" in last(), "«⬅️ меню» из карточки")
c = Call(504, "spo:3"); run(SH.one_callback(c)); check("#3" in SENT[-1][0], "уведомление автору → «📍 посмотреть место» в боте")
c = Call(500, "spo:5"); run(SH.one_callback(c)); check(c.alerts and "yo'q" in c.alerts[0].lower(), "чужое непроверенное — не показываем")
check("spo:3" in btns(SH._map_kb(FB, "uz", 3)), "в уведомлении автору — кнопка «посмотреть» (работает без Mini App)")
print(f"OK: {ok} проверок")
