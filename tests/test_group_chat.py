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
async def fake_answer(q, asker="", context=""):
    ASKED.append((q, asker, context)); return "Короче, бро — чётко 💪"
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

asyncio.get_event_loop().run_until_complete(main())

# стиль: в инструкции есть «дерзко, но без грубости»
check("Never insult" in ai._GROUP_SYSTEM and "SAME language" in ai._GROUP_SYSTEM and "ONLY the HANDBOOK" in ai._GROUP_SYSTEM,
      "инструкция стиля: дерзко, но без оскорблений; язык вопроса; факты о проекте только из справочника")
print(f"OK: {ok} проверок")
