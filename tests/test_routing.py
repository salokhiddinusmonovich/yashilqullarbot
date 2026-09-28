import os, sys, asyncio, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.conf import settings; settings.MEDIA_ROOT = tempfile.mkdtemp()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from app_telegram.models import TGUser
import bot as B
OUT = []
async def fake_send(self, chat_id, text, *a, **k): OUT.append(text); return None
Bot.send_message = fake_send
class Cfg:
    class misc: miniapp_url = "https://app.yashilqollar.uz"
    class tg_bot: admin_ids = []
bot = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"); bot["config"] = Cfg
dp = Dispatcher(bot, storage=MemoryStorage())
B.register_all_filters(dp); B.register_all_handlers(dp)
try:
    B.register_all_middlewares(dp, Cfg)
except Exception as e:
    print("middlewares skipped:", e)
TGUser.objects.create(tg_id=700, fullname="Test", region="jizzakh")
def upd(text, uid=700):
    return types.Update(**{"update_id": 1, "message": {"message_id": 1, "date": 0, "text": text,
        "chat": {"id": uid, "type": "private"}, "from": {"id": uid, "is_bot": False, "first_name": "T"},
        **({"entities": [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]} if text.startswith("/") else {})}})
ok = 0
for text, want in (("📍 Iflos joy", "Iflos joylar"), ("📍 Грязное место", "Iflos joylar"), ("/iflos", "Iflos joylar"), ("/start spot", "1/6")):
    OUT.clear(); Dispatcher.set_current(dp); Bot.set_current(bot)
    asyncio.run(dp.process_update(upd(text)))
    good = any(want in x for x in OUT)
    ok += good
    print(("✓" if good else "✗"), repr(text), "→", [x[:50] for x in OUT])
print(f"OK: {ok}/4")
