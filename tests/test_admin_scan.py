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
from datetime import timedelta
import qrcode
from PIL import Image
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.handler import SkipHandler
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
from app_telegram import services as S
from API import webapp as W
from tgbot.handlers import admin_scan as AS, start as ST
from tgbot.i18n import current_lang
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
now = timezone.now()
admin = TGUser.objects.create(tg_id=1, fullname="Salohiddin", region="tashkent_s", is_admin=True)        # роль «Волонтёр», но is_admin
coord = TGUser.objects.create(tg_id=2, fullname="Samarqand koord", region="samarkand", role="coordinator")
vol = TGUser.objects.create(tg_id=3, fullname="Dilnoza Fargona", region="fargona")
ev_far_old = EcoProject.objects.create(title="Farg'ona subbotnik", region="fargona", date=now - timedelta(days=12), location_name="x")
ev_sam_old = EcoProject.objects.create(title="Samarqand plogging", region="samarkand", date=now - timedelta(days=5), location_name="x")
ev_sam_new = EcoProject.objects.create(title="Samarqand bugun", region="samarkand", date=now - timedelta(hours=1), location_name="x")
ev_ancient = EcoProject.objects.create(title="Juda eski", region="fargona", date=now - timedelta(days=90), location_name="x")

# ── права ──
check(S.is_staff(admin) and S.scan_regions(admin) is None and S.scan_back_days(admin) == 60, "is_admin (даже с ролью «Волонтёр») — сканер, все регионы, 60 дней")
check(S.scan_regions(coord) == ["samarkand"] and S.scan_back_days(coord) == 1, "координатор — только свой регион, со вчерашнего дня")
check(not S.is_staff(vol), "обычный волонтёр — не сканирует")

# ── Mini App: список мероприятий в сканере ──
f = APIRequestFactory()
def get(view, u):
    req = f.get("/x"); force_authenticate(req, user=u); return view(req)
def post(view, u, data):
    req = f.post("/x", data, format="json"); force_authenticate(req, user=u); return view(req)
ids = [e["id"] for e in get(W.StaffEventsView.as_view(), admin).data["events"]]
check(ev_far_old.id in ids and ev_sam_old.id in ids and ev_ancient.id not in ids and get(W.StaffEventsView.as_view(), admin).data["admin"], "админ: Фергана 12 дней назад и Самарканд — видны; 90 дней — нет")
ids_c = [e["id"] for e in get(W.StaffEventsView.as_view(), coord).data["events"]]
check(ids_c == [ev_sam_new.id], "координатор Самарканда: только сегодняшнее в Самарканде (как раньше)")
r = post(W.StaffCheckInView.as_view(), admin, {"project_id": ev_far_old.id, "qr": f"https://t.me/yashilqollarbot?start=qr_{vol.tg_id}"}).data
check(r["result"] == "ok" and PP.objects.get(user=vol, project=ev_far_old).status == "attended", "админ отметил фергана-волонтёра на прошедшем мероприятии в Фергане")
check(post(W.StaffCheckInView.as_view(), coord, {"project_id": ev_far_old.id, "user_id": vol.id}).data["result"] == "other_region", "координатор Самарканда — Фергану нельзя")
r = post(W.StaffCheckInView.as_view(), admin, {"project_id": ev_sam_old.id, "user_id": vol.id}).data
check(r["result"] == "wrong_region" and "Farg" in r["person_region"] and not PP.objects.filter(user=vol, project=ev_sam_old).exists(), "даже админ: ферганца на самаркандское — нельзя (wrong_region)")
r = post(W.StaffCheckInView.as_view(), admin, {"project_id": ev_sam_old.id, "user_id": vol.id, "force": True}).data
check(r["result"] == "wrong_region", "и «force» больше не помогает")

# ── бот ──
bot = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw")
dp = Dispatcher(bot, storage=MemoryStorage()); Dispatcher.set_current(dp)
SENT = []
class FB:
    def get(self, k, d=None): return None
    async def send_message(self, tg, text, reply_markup=None, **k): SENT.append(("to", tg, text))
class Msg:
    def __init__(self, uid, text=None, args="", photo=None):
        self.from_user = type("U", (), {"id": uid, "full_name": "X", "username": None})(); self.chat = type("C", (), {"id": uid})()
        self.text = text; self._args = args; self.photo = photo; self.document = None; self.bot = FB(); self.kb = None
    def get_args(self): return self._args
    async def answer(self, text, reply_markup=None, **k): SENT.append(("me", text, reply_markup)); self.kb = reply_markup
    async def edit_text(self, text, reply_markup=None, **k): SENT.append(("me", text, reply_markup)); self.kb = reply_markup
class Call:
    def __init__(self, uid, data):
        self.from_user = type("U", (), {"id": uid})(); self.data = data; self.message = Msg(uid); self.bot = FB(); self.alerts = []
    async def answer(self, text=None, show_alert=False, **k): self.alerts.append(text)
def st(uid):
    types.Chat.set_current(types.Chat(id=uid, type="private")); types.User.set_current(types.User(id=uid))
    return dp.current_state(chat=uid, user=uid)
btns = lambda kb: [b.callback_data for row in kb.inline_keyboard for b in row] if kb else []
run = asyncio.run

m = Msg(1, "/start qr_3", args="qr_3"); run(ST.user_start(m, st(1)))
text, kb = SENT[-1][1], SENT[-1][2]
check("Dilnoza" in text and btns(kb) == [f"qa:3:{ev_far_old.id}"] and "✅" in kb.inline_keyboard[0][0].text,
      "админ открыл QR-ссылку → только мероприятия Ферганы (его регион), без «все регионы»; 90 дней назад — нет")
c = Call(1, f"qa:3:{ev_sam_old.id}"); run(AS.mark_callback(c))
check(c.alerts and "⛔" in c.alerts[0] and not PP.objects.filter(user=vol, project=ev_sam_old).exists(), "подставил самаркандское мероприятие — «⛔️ другой регион», не отмечено")
ev_far_new = EcoProject.objects.create(title="Farg'ona plogging", region="fargona", date=now - timedelta(days=3), location_name="x")
SENT.clear(); c = Call(1, f"qa:3:{ev_far_new.id}"); run(AS.mark_callback(c))
check(PP.objects.get(user=vol, project=ev_far_new).status == "attended" and "belgilandi" in SENT[0][1], "ферганское 3 дня назад — отмечен")
check(any(x[0] == "to" and x[1] == 3 for x in SENT), "волонтёру — уведомление «вам засчитано»")
c = Call(1, f"qa:3:{ev_far_new.id}"); run(AS.mark_callback(c)); check("allaqachon" in SENT[-1][1], "повторно — «уже отмечен»")
noreg = TGUser.objects.create(tg_id=4, fullname="Regionsiz", region=None)
run(AS.admin_pick(Msg(1), 4)); b = btns(SENT[-1][2])
check(f"qa:4:{ev_sam_old.id}" in b and f"qa:4:{ev_far_new.id}" in b, "у человека нет региона — видны все регионы")
c = Call(2, f"qa:3:{ev_far_old.id}"); run(AS.mark_callback(c)); check(c.alerts and c.alerts[0], "координатор не может нажать админские кнопки")

# координатор по QR-ссылке — как раньше (сам выбирается сегодняшний в его регионе)
SENT.clear(); run(ST.user_start(Msg(2, "/start qr_3", args="qr_3"), st(2)))
check(any("⛔" in x[1] for x in SENT if x[0] == "me") and not PP.objects.filter(user=vol, project=ev_sam_new).exists(),
      "координатор Самарканда сканирует ферганца — «⛔️ другой регион», на самаркандское не отмечен (раньше отмечал!)")
samv = TGUser.objects.create(tg_id=5, fullname="Samarqandlik", region="samarkand")
SENT.clear(); run(ST.user_start(Msg(2, "/start qr_5", args="qr_5"), st(2)))
check(PP.objects.get(user=samv, project=ev_sam_new).status == "attended", "самаркандца — на сегодняшнее самаркандское, как раньше")

# скриншот QR
def shot(text, w=1080, h=2000):
    q = qrcode.make(text).convert("RGB").resize((520, 520))
    bg = Image.new("RGB", (w, h), (24, 34, 28)); bg.paste(q, (280, 700))
    b = io.BytesIO(); bg.save(b, "JPEG", quality=85); return b.getvalue()
check(AS.read_qr(shot("https://t.me/yashilqollarbot?start=qr_3")) == 3, "QR со скриншота читается (zxing-cpp)")
check(AS.read_qr(shot("просто текст")) is None, "картинка без нашего QR — None")
class Ph:
    def __init__(self, data): self.data = data
    async def download(self, destination_file): destination_file.write(self.data)
SENT.clear(); run(AS.qr_photo(Msg(1, photo=[Ph(shot("https://t.me/yashilqollarbot?start=qr_3"))])))
check("Dilnoza" in SENT[-1][1] and btns(SENT[-1][2])[0].startswith("qa:3:"), "админ переслал скриншот → «на какое мероприятие отметить Dilnoza?»")
for uid, data, why in ((2, shot("https://t.me/yashilqollarbot?start=qr_3"), "не админ"), (1, shot("hello"), "фото без QR")):
    try:
        run(AS.qr_photo(Msg(uid, photo=[Ph(data)]))); skipped = False
    except SkipHandler:
        skipped = True
    check(skipped, f"{why} — фото идёт дальше другим обработчикам")

# /belgila
SENT.clear(); run(AS.belgila_handler(Msg(1, "/belgila Dilnoza", args="Dilnoza")))
check(btns(SENT[-1][2]) == ["qu:3"], "/belgila Dilnoza → нашёлся")
c = Call(1, "qu:3"); run(AS.user_callback(c)); check("Dilnoza" in SENT[-1][1] and btns(c.message.kb)[0].startswith("qa:3:"), "выбрал человека → выбор мероприятия")
from tgbot.i18n import t as T
run(AS.belgila_handler(Msg(2, "/belgila Dilnoza", args="Dilnoza"))); check(SENT[-1][1] == T("qr_no_rights"), "координатору /belgila — нет прав")

# настоящая маршрутизация: админ шлёт фото в бот
import bot as B
OUT = []
async def fake_send(self, chat_id, text, *a, **k): OUT.append(text)
Bot.send_message = fake_send
async def fake_dl(self, destination_file=None, **k): destination_file.write(shot("https://t.me/yashilqollarbot?start=qr_3")); return destination_file
types.PhotoSize.download = fake_dl
class Cfg:
    class misc: miniapp_url = None
bot2 = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"); bot2["config"] = Cfg
dp2 = Dispatcher(bot2, storage=MemoryStorage()); B.register_all_filters(dp2); B.register_all_handlers(dp2)
Dispatcher.set_current(dp2); Bot.set_current(bot2)
upd = types.Update(**{"update_id": 9, "message": {"message_id": 1, "date": 0, "chat": {"id": 1, "type": "private"},
      "from": {"id": 1, "is_bot": False, "first_name": "S"}, "photo": [{"file_id": "F", "file_unique_id": "U", "width": 1080, "height": 2000}]}})
run(dp2.process_update(upd))
check(any("Dilnoza" in x for x in OUT), f"в живом боте: фото QR от админа → выбор мероприятия ({[x[:40] for x in OUT]})")
print(f"OK: {ok} проверок")
