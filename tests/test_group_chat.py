"""💬 Ассистент в группе: когда отвечает, когда молчит, анти-спам; меню личного чата в группе не срабатывает."""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from tgbot.services import ai
from tgbot.handlers import group_chat as G
from tgbot.i18n import current_lang
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)

bot = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage()); Dispatcher.set_current(dp); Bot.set_current(bot)
SENT, ASKED = [], []
async def send_message(chat_id, text, **k): SENT.append((chat_id, text, k.get("reply_to_message_id")))
async def nothing(*a, **k): return True
async def get_me(): return types.User(id=999, is_bot=True, first_name="YQ", username="yashilqollarbot")
bot.send_message = send_message; bot.send_chat_action = nothing; bot.get_me = get_me
ai.enabled = lambda: True
SKIPNEXT = [False]
async def fake_answer(q, asker="", context="", allow_skip=False):
    ASKED.append((q, asker, context, allow_skip))
    if allow_skip and SKIPNEXT[0]: return ""
    return "Короче, бро — чётко 💪"
ai.group_answer = fake_answer

import bot as BOT
BOT.register_all_handlers(dp)                         # вся маршрутизация как в бою

uid = [100]
def upd(text, chat="yashilqollarchat", chat_id=-1001, reply_to=None, user=None, **extra):
    uid[0] += 1
    m = {"message_id": uid[0], "date": 0, "text": text, "chat": {"id": chat_id, "type": "supergroup", "username": chat, "title": "chat"},
         "from": user or {"id": uid[0], "is_bot": False, "first_name": "Ali"}}
    if reply_to: m["reply_to_message"] = reply_to
    m.update(extra)
    return types.Update(update_id=uid[0], message=m)
async def run(u):
    SENT.clear(); ASKED.clear(); await dp.process_update(u); return list(SENT)

async def main():
    r = await run(upd("@yashilqollarbot qachon keyingi tadbir"))
    check(r and r[0][2] and ASKED[0][0] == "qachon keyingi tadbir", "упоминание → ответ реплаем; @ник из вопроса убран")
    r = await run(upd("Sertifikat qayerdan olsam bo'ladi?"))
    check(r and ASKED, "вопрос со «?» в группе → ответ")
    r = await run(upd("salom hammaga"))
    check(not r and not ASKED, "обычная болтовня без вопроса — молчит")
    r = await run(upd("nima?"))
    check(not r, "«nima?» (меньше 3 слов) — не вопрос к боту")
    r = await run(upd("когда будет у вас еще event"))
    check(r and ASKED and ASKED[0][3] is True, "вопрос БЕЗ «?» («когда будет у вас еще event») → ответ, ИИ может решить SKIP")
    r = await run(upd("keyingi tadbir qachon bo'ladi"))
    check(r and ASKED[0][3] is True, "узбекский без «?» (qachon) → ответ")
    r = await run(upd("sertifikat berishadimi endi"))
    check(r, "узбекское «-mi» без «?» (berishadimi) → ответ")
    SKIPNEXT[0] = True
    r = await run(upd("как дела у тебя братан"))
    check(ASKED and not r, "похоже на вопрос, но болтовня → ИИ сказал SKIP → бот молчит")
    SKIPNEXT[0] = False
    r = await run(upd("Sertifikat qayerdan olsam bo'ladi?"))
    check(r and ASKED[0][3] is False, "явный вопрос со «?» — отвечает всегда (без SKIP)")
    bot_msg = {"message_id": 5, "date": 0, "text": "Короче, бро — чётко 💪", "chat": {"id": -1001, "type": "supergroup"},
               "from": {"id": 999, "is_bot": True, "first_name": "YQ", "username": "yashilqollarbot"}}
    r = await run(upd("a nechida boshlanadi", reply_to=bot_msg))
    check(r and ASKED and "bot (you)" in ASKED[0][2], "ответ на сообщение бота → диалог, бот видит своё прошлое сообщение")
    r = await run(upd("Qachon bo'ladi bu tadbir?", chat="boshqa_guruh", chat_id=-2002))
    check(not r and not ASKED, "чужая группа (не в GROUP_AI_CHATS) — молчит")
    r = await run(upd("Post kanaldan?", user={"id": 777000, "is_bot": False, "first_name": "Telegram"}))
    check(not r, "автопересылка поста канала в обсуждения — не отвечаем")
    # анти-спам: тот же человек дважды подряд
    same = {"id": 5555, "is_bot": False, "first_name": "Bek"}
    r1 = await run(upd("Qanday qilib ro'yxatdan o'taman?", user=same))
    r2 = await run(upd("Yana bitta savol bormi menda?", user=same))
    check(r1 and not r2, f"один человек — не чаще раза в {G.USER_COOLDOWN} c")
    # меню личного чата в группе не срабатывает
    r = await run(upd("🌱 Tadbirlar"))
    check(not r, "кнопка меню текстом в группе — бот не открывает меню")
    r = await run(upd("/start"))
    check(not r, "/start в группе — ничего")
    # ИИ недоступен: на прямое обращение — честный ответ, на просто «?» — молчим
    async def down(*a, **k): raise ai.Unavailable("rate limit")
    ai.group_answer = down
    r = await run(upd("@yashilqollarbot bu loyiha nima o'zi"))
    check(r and ("dam olyapti" in r[0][1] or len(r[0][1]) > 20), "ИИ на лимите, а бота позвали — отвечает (справочник или «позже»)")
    r = await run(upd("Ertaga havo qanday bo'ladi?"))
    check(not r, "ИИ на лимите и просто вопрос — молчит, не спамит")

STICK, REACT = [], []
async def get_sticker_set(name):
    return types.StickerSet(name=name, title="t", is_animated=False, stickers=[
        {"file_id": "S_LOL", "file_unique_id": "u1", "width": 1, "height": 1, "is_animated": False, "emoji": "😂"},
        {"file_id": "S_COOL", "file_unique_id": "u2", "width": 1, "height": 1, "is_animated": False, "emoji": "😎"}])
async def send_sticker(chat_id, sticker, **k): STICK.append(sticker)
async def request(method, data=None, *a, **k): REACT.append((method, data)); return True
bot.get_sticker_set = get_sticker_set; bot.send_sticker = send_sticker; bot.request = request

async def fun():
    async def tagged(q, asker="", context="", allow_skip=False): return "Ха, чётко бро 😎\nREACT:🔥\nSTICKER:😂"
    ai.group_answer = tagged
    r = await run(upd("@yashilqollarbot qalesan bro", user={"id": 8001, "is_bot": False, "first_name": "Ali"}))
    check(r and "REACT" not in r[0][1] and "STICKER" not in r[0][1], "теги REACT/STICKER из текста вырезаны")
    check(STICK == ["S_LOL"], "стикер с нужным эмодзи из пака MemesMusa")
    check(REACT and REACT[0][0] == "setMessageReaction" and "🔥" in REACT[0][1]["reaction"], "реакция 🔥 на сообщение")
    STICK.clear()
    await run(upd("@yashilqollarbot yana bitta", user={"id": 8002, "is_bot": False, "first_name": "Ali"}))
    check(not STICK, f"второй стикер подряд — нет (не чаще раза в {G.STICKER_GAP} c)")
    check(G.split_tags("Salom\nREACT:🤡") == ("Salom", "🤡", ""), "split_tags")

async def resilient():
    # Gemini зависает (asyncio.TimeoutError в Python 3.10) / модель отключили (404) → не падаем, отвечает Groq
    import importlib
    A = importlib.import_module("tgbot.services.ai")
    A.API_KEY, A.GROQ_KEY = "k", "g"
    calls = []
    async def post(model, body):
        calls.append(model)
        if model == A.MODELS[0]: raise asyncio.TimeoutError()
        return 404, {"error": {"message": "no longer available"}}
    async def groq(system, history, text, json_mode, max_tokens): return "Groq ответил"
    A._post, A._groq_chat = post, groq
    out = await A._generate("s", [{"role": "user", "parts": [{"text": "q"}]}], small=("s", [], "q"))
    check(out == "Groq ответил" and len(calls) == len(A.MODELS), "Gemini завис/404 → бот не падает, отвечает Groq")
    check(await A._dead_ttl(A.MODELS[1]) > 3600, "отключённая модель (404) пропускается сутки")
    calls.clear()
    out = await A._generate("s", [], small=("s", [], "q"), groq_first=True)
    check(out == "Groq ответил" and not calls, "в группе Groq первым — Gemini даже не трогаем")

asyncio.get_event_loop().run_until_complete(main())
asyncio.get_event_loop().run_until_complete(fun())
asyncio.get_event_loop().run_until_complete(resilient())

# стиль: в инструкции есть «дерзко, но без грубости»
check("SKIP" in ai._SKIP_RULE and "UPCOMING EVENTS" in ai._GROUP_SYSTEM and "Never make up a date" in ai._GROUP_SYSTEM,
      "инструкция: реальные ближайшие мероприятия, без выдуманных дат, «SKIP» для болтовни")
check("Never insult" in ai._GROUP_SYSTEM and "SAME language" in ai._GROUP_SYSTEM and "ONLY the HANDBOOK" in ai._GROUP_SYSTEM,
      "инструкция стиля: дерзко, но без оскорблений; язык вопроса; факты о проекте только из справочника")
print(f"OK: {ok} проверок")
