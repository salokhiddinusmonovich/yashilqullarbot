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
CALLS = []
async def gem(request):
    b = await request.json(); CALLS.append(1)
    audio = any("inline_data" in p for p in b["contents"][-1]["parts"])
    txt = "🎙 «Привет! Я не могу получить сертификат»\nСертификат приходит в бот на следующее утро: /sertifikat" if audio else "Ответ ИИ"
    return web.json_response({"candidates": [{"content": {"parts": [{"text": txt}]}}]})
SENT = []
class Voice:
    duration = 4
    async def download(self, destination_file=None, **k): destination_file.write(b"OggS"); return destination_file
class Bot:
    async def send_chat_action(self, *a): pass
class Msg:
    def __init__(self, text=None, voice=False):
        self.text = text; self.voice = Voice() if voice else None; self.audio = None
        self.from_user = type("U", (), {"id": 5})(); self.chat = type("C", (), {"id": 5})(); self.bot = Bot()
    async def answer(self, text, reply_markup=None, **k): SENT.append(text)
async def main():
    app = web.Application(); app.router.add_post("/v1beta/models/{m}", gem)
    r = web.AppRunner(app); await r.setup(); await web.TCPSite(r, "127.0.0.1", 8918).start()
    ai.URL = "http://127.0.0.1:8918/v1beta/models/{model}:generateContent"; ai.API_KEY = "k"
    TGUser.objects.create(tg_id=5, fullname="Salokhiddin Usmonov", role="Founder", region="tashkent_s")
    current_lang.set("ru")
    check(ai.DAILY_LIMIT == 0, "личного лимита по умолчанию нет")
    for i in range(40):                      # 40 вопросов подряд — ни одного «лимит исчерпан»
        await A.free_question(Msg(f"Скажите пожалуйста подробно вопрос номер {i} про мероприятия и баллы"), None)
    check(not any("Лимит вопросов" in x for x in SENT) and len(CALLS) == 40, "40 вопросов подряд — без «лимит исчерпан»")
    await A.free_question(Msg(voice=True), None)
    check("сертификат" in SENT[-1].lower(), "голосовое про сертификат → ответ")
    n = len(CALLS)
    for q in ["привет", "Алооо", "Твотвовов", "Бл", "Эххх", "salom", "?", "rahmat"]:
        await A.free_question(Msg(q), None)
        check("помощник Yashil" in SENT[-1], f"«{q}» → приветствие без ИИ")
    check(len(CALLS) == n, "на приветствия/мусор ИИ не тратится")
    await A.free_question(Msg("Почему админ не пишет"), None)
    check(len(CALLS) == n + 1 or "Кому написать" in SENT[-1], "«Почему админ не пишет» — это вопрос, отвечаем")
    await r.cleanup()
asyncio.run(main()); print(f"OK: {ok} проверок")
