import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True)
import fakeredis.aioredis; L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
SENT = []
import app_telegram.telegram as TT; TT.send_in_background = lambda m, on_done=None: SENT.extend(m)
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
from app_telegram import waitlist, services
from API import webapp as W
from tgbot.handlers import reminders as RH, ecoclub as EC
from tgbot.i18n import current_lang
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
ev = EcoProject.objects.create(title="Daraxt ekish", region="tashkent_s", date=timezone.now() + timedelta(days=2), is_active=True,
                               location_name="Yunusobod", max_participants=2, chat_link="https://t.me/+g")
U = [TGUser.objects.create(tg_id=100 + i, fullname=f"U{i}", region="tashkent_s") for i in range(5)]
sam = TGUser.objects.create(tg_id=200, fullname="Sam", region="samarkand")
services.join_event(U[0], ev.id); services.join_event(U[1], ev.id)
check(services.join_event(U[2], ev.id)[0] == "full", "2 места заняты → «мест нет»")
f = APIRequestFactory()
def api(user, view, data=None, **kw):
    req = f.post("/x", data or {}, format="json"); force_authenticate(req, user=user); return view.as_view()(req, **kw).data
r = api(U[2], W.WaitView, pk=ev.id); check(r["result"] == "waiting" and r["event"]["my_wait"] == 1 and r["event"]["waitlist"] == 1, "Mini App: встал в очередь №1")
api(U[3], W.WaitView, pk=ev.id); r = api(U[4], W.WaitView, pk=ev.id); check(r["event"]["my_wait"] == 3, "третий в очереди — №3")
check(api(sam, W.WaitView, pk=ev.id)["result"] == "region", "чужой регион в очередь не встаёт")
r = api(U[4], W.WaitView, {"leave": True}, pk=ev.id); check(r["result"] == "left" and waitlist.count(ev.id) == 2, "выйти из очереди")

# «❌ Kelolmayman» → место первому из очереди
class Msg:
    def __init__(self): self.out = []
    async def answer(self, text, **k): self.out.append((text, k.get("reply_markup")))
    async def edit_reply_markup(self, *a): pass
class Call:
    def __init__(self, data, uid): self.data = data; self.from_user = type("U", (), {"id": uid})(); self.message = Msg(); self.bot = None
    async def answer(self, *a, **k): pass
asyncio.run(RH.rem_callback(Call(f"rem:no:{ev.id}", 100)))
check(PP.objects.filter(user=U[2], project=ev, status="approved").exists() and waitlist.position(U[2].id, ev.id) is None, "«Kelolmayman» у U0 → U2 из очереди записан")
check(SENT and SENT[-1][0] == 102 and "Joy bo'shadi" in SENT[-1][1] and "https://t.me/+g" in SENT[-1][1], "U2 получил «🎉 Освободилось место!» со ссылкой на группу")
# админ отклонил запись → следующий
p1 = PP.objects.get(user=U[1], project=ev); p1.status = "rejected"; p1.save()
check(PP.objects.filter(user=U[3], project=ev, status="approved").exists(), "админ отклонил U1 → записан U3")
# увеличили число мест → из очереди (пусто — ничего не ломается)
waitlist.join(U[4], ev); ev.max_participants = 5; ev.save()
check(PP.objects.filter(user=U[4], project=ev, status="approved").exists(), "увеличили места → очередь записана")
# удаление мероприятия не записывает никого заново
ev2 = EcoProject.objects.create(title="X", region="tashkent_s", date=timezone.now() + timedelta(days=3), is_active=True, location_name="x", max_participants=1)
services.join_event(U[0], ev2.id); waitlist.join(U[1], ev2); ev2.delete()
check(not PP.objects.filter(project_id=ev2.id).exists(), "удалили мероприятие — никого не записали, без ошибок")
# бот: мест нет → кнопка очереди
ev3 = EcoProject.objects.create(title="Full", region="tashkent_s", date=timezone.now() + timedelta(days=3), is_active=True, location_name="x", max_participants=1)
services.join_event(U[0], ev3.id)
async def run():
    m = Msg(); EC._is_subscribed = lambda *a: asyncio.sleep(0, True)
    await EC._do_register(m, 101, ev3.id, None)
    return m
m = asyncio.run(run())
check("Navbatga" in str(m.out[-1][0]) and m.out[-1][1].inline_keyboard[0][0].callback_data == f"evwait:{ev3.id}", "бот: «мест нет» + кнопка «⏳ Navbatga yozilish»")
c = Call(f"evwait:{ev3.id}", 101); asyncio.run(EC.wait_callback(c))
check("№1" in c.message.out[-1][0], "бот: «Вы в очереди №1»")
print(f"OK: {ok} проверок")
