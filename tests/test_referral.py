"""👥 «Пригласи друга» через ворота подписки: ссылка ref_ не теряется, бонус пригласившему — при первом приходе друга."""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
import app_telegram.telegram as TT
SENT = []; TT.send_in_background = lambda m, on_done=None: SENT.extend(m)
from django.utils import timezone
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.handler import CancelHandler
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
from app_telegram import referrals, services
from tgbot.i18n import current_lang
from tgbot.middlewares.subscription import SubscriptionMiddleware
from tgbot.handlers import start as ST
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)

bot = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw")
dp = Dispatcher(bot, storage=MemoryStorage()); Dispatcher.set_current(dp); Bot.set_current(bot)
MEMBER = {}
async def get_chat_member(chat_id, user_id):
    return types.ChatMember(status=MEMBER.get(user_id, "left"), user={"id": user_id, "is_bot": False, "first_name": "x"})
async def nothing(*a, **k): return True
bot.get_chat_member = get_chat_member; bot.send_message = nothing
ST.ask_language = nothing                                  # новый человек → выбор языка; здесь не важен

def msg(tg, text):
    return types.Message.to_object({"message_id": 1, "date": 0, "text": text, "chat": {"id": tg, "type": "private"},
                                    "from": {"id": tg, "is_bot": False, "first_name": "Ali"}})
mw = SubscriptionMiddleware()
async def through(m):
    """Как в боте: сначала ворота подписки, потом /start."""
    try: await mw.on_pre_process_message(m, {})
    except CancelHandler: return False
    await ST.user_start(m, dp.current_state(chat=m.chat.id, user=m.from_user.id)); return True

inviter = TGUser.objects.create(tg_id=100, fullname="Aziza Rahimova", region="tashkent_s", balance=20)
ev = EcoProject.objects.create(title="Daraxt ekish", date=timezone.now(), region="tashkent_s", max_participants=50)

async def main():
    # друг открыл ссылку, не подписан → ворота
    check(not await through(msg(200, "/start ref_100")), "по ссылке без подписки — экран «подпишитесь»")
    check(not await through(msg(200, "/start")), "ещё раз пустой /start (не подписан) — снова ворота")
    MEMBER[200] = "member"
    check(await through(msg(200, "/start")), "подписался и прислал ОБЫЧНЫЙ /start (не «Obuna bo'ldim»)")
    check(L._sync.get("ref:by:200") == "100", "приглашение не потерялось: друг записан за Aziza")
    check(referrals.stats(100)["invited"] == 1, "у Aziza «Taklif qilganlar: 1»")
    # подписан сразу — обычный путь
    MEMBER[201] = "member"
    await through(msg(201, "/start ref_100"))
    check(L._sync.get("ref:by:201") == "100" and referrals.stats(100)["invited"] == 2, "подписанный друг по ссылке — тоже записан")
    # бонус — при первом приходе друга
    friend = TGUser.objects.create(tg_id=200, fullname="Jasur Tursunov", region="tashkent_s")
    services.check_in(friend, ev)
    inviter.refresh_from_db(); friend.refresh_from_db()
    check(friend.balance == 10, "друг пришёл: +10 баллов ему")
    check(inviter.balance == 20 + referrals.BONUS, f"пригласившему +{referrals.BONUS} баллов")
    check(any(tg == 100 for tg, _ in SENT), "пригласившему сообщение «+5 ball»")
    ev2 = EcoProject.objects.create(title="Plogging", date=timezone.now(), region="tashkent_s", max_participants=50)
    services.check_in(friend, ev2); inviter.refresh_from_db()
    check(inviter.balance == 20 + referrals.BONUS, "второй приход друга — бонус не повторяется")
    check(referrals.stats(100)["joined"] == 1, "«kelganlar: 1»")

asyncio.get_event_loop().run_until_complete(main())
print(f"OK: {ok} проверок")
