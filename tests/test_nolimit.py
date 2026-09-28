import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
L._sync = fakeredis.FakeRedis(decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(decode_responses=True)
from aiohttp import web
from app_telegram.models import TGUser
from tgbot.services import ai
from tgbot.handlers import assistant as A
from tgbot.i18n import current_lang
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)
async def gem(request):   # Google: дневной лимит на всём
    return web.json_response({"error": {"code": 429, "message": "quota GenerateRequestsPerDayPerProjectPerModel-FreeTier"}}, status=429)
SENT = []
class Voice:
    duration = 4
    async def download(self, destination_file=None, **k): destination_file.write(b"OggS"); return destination_file
class Bot:
    config = type("C", (), {"tg_bot": type("T", (), {"admin_ids": [5]})()})()
    def __getitem__(self, k): return self.config
    async def send_chat_action(self, *a): pass
class Msg:
    def __init__(self, text=None, voice=False):
        self.text = text; self.voice = Voice() if voice else None; self.audio = None
        self.from_user = type("U", (), {"id": 5})(); self.chat = type("C", (), {"id": 5})(); self.bot = Bot()
    async def answer(self, text, reply_markup=None, **k): SENT.append((text, reply_markup))
class Call:
    def __init__(self, d): self.data = d; self.message = Msg()
    async def answer(self, *a, **k): pass
async def main():
    app = web.Application(); app.router.add_post("/v1beta/models/{m}", gem)
    r = web.AppRunner(app); await r.setup(); await web.TCPSite(r, "127.0.0.1", 8919).start()
    ai.URL = "http://127.0.0.1:8919/v1beta/models/{model}:generateContent"; ai.API_KEY = "k"
    TGUser.objects.create(tg_id=5, fullname="Salokhiddin Usmonov", role="Founder", region="tashkent_s", is_admin=True)
    current_lang.set("ru")
    busy = lambda: any("занят" in x[0] or "Лимит" in x[0] for x in SENT)
    await A.free_question(Msg("hu"), None)
    check("помощник" in SENT[-1][0] and SENT[-1][1].inline_keyboard[0][0].callback_data.startswith("faq:"), "«hu» → приветствие + кнопки тем")
    await A.free_question(Msg("Привет! Я не могу получить сертификат, не могу связаться с админом. Почему так?"), None)
    check("Сертификат" in SENT[-1][0] and SENT[-1][1] is not None, "Google на лимите → ближайший готовый ответ (сертификат) + кнопки")
    await A.free_question(Msg("Почему небо голубое и что будет завтра в мире вообще"), None)
    check("Выберите тему" in SENT[-1][0], "совсем не по теме → «выберите тему» + кнопки")
    await A.free_question(Msg(voice=True), None)
    check("голосовое" in SENT[-1][0] and SENT[-1][1] is not None, "голос при лимите → кнопки тем, не «занят»")
    await A.cmd_message(Msg(voice=True), None)
    check(SENT[-1][1] is not None and not busy(), "админ голосом при лимите → кнопки, не «занят»")
    c = Call("faq:certificate"); await A.faq_callback(c)
    check("Сертификат" in SENT[-1][0], "кнопка темы → готовый ответ")
    check(not busy(), "ни одного «занят / лимит исчерпан»")
    await r.cleanup()
asyncio.run(main()); print(f"OK: {ok} проверок")
