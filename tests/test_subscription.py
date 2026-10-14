"""📢 Обязательная подписка на @yashilqollar: middleware, кэш, «✅ Я подписался», продолжение deep-link."""
import os, sys, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
import fakeredis, fakeredis.aioredis, tgbot.services.lang as L
srv = fakeredis.FakeServer(); L._sync = fakeredis.FakeRedis(server=srv, decode_responses=True); L._async = fakeredis.aioredis.FakeRedis(server=srv, decode_responses=True)
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.handler import CancelHandler
from aiogram.utils import exceptions
from tgbot.i18n import current_lang, t
from tgbot.services import subscription as S
from tgbot.middlewares.subscription import SubscriptionMiddleware
from tgbot.handlers import subscriptions as H, start as ST, spots as SPH
current_lang.set("uz")
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)

bot = Bot(token="123456:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw")
dp = Dispatcher(bot, storage=MemoryStorage()); Dispatcher.set_current(dp); Bot.set_current(bot)
MEMBERS = {}        # tg → status | Exception
CALLS = []
SENT = []
async def get_chat_member(chat_id, user_id):
    CALLS.append(user_id)
    v = MEMBERS.get(user_id, "left")
    if isinstance(v, Exception): raise v
    return types.ChatMember(status=v, user={"id": user_id, "is_bot": False, "first_name": "x"})
async def send_message(chat_id, text, reply_markup=None, **k): SENT.append((chat_id, text, reply_markup))
async def answer_callback_query(*a, **k): SENT.append(("alert", k.get("text") or (a[1] if len(a) > 1 else None), None))
async def nothing(*a, **k): return True
bot.get_chat_member = get_chat_member; bot.send_message = send_message
bot.answer_callback_query = answer_callback_query; bot.delete_message = nothing; bot.edit_message_reply_markup = nothing

def msg(tg, text, chat_type="private"):
    m = types.Message.to_object({"message_id": 1, "date": 0, "text": text,
        "chat": {"id": tg if chat_type == "private" else -100, "type": chat_type},
        "from": {"id": tg, "is_bot": False, "first_name": "Ali"}})
    return m
def cb(tg, data):
    return types.CallbackQuery.to_object({"id": "1", "chat_instance": "c", "data": data,
        "from": {"id": tg, "is_bot": False, "first_name": "Ali"},
        "message": {"message_id": 5, "date": 0, "text": "gate", "chat": {"id": tg, "type": "private"},
                    "from": {"id": 999, "is_bot": True, "first_name": "Bot"}}})

mw = SubscriptionMiddleware()
async def passes(coro):
    try: await coro; return True
    except CancelHandler: return False

async def main():
    # не подписан → экран подписки, хендлер не идёт, ссылка запомнена
    SENT.clear()
    check(not await passes(mw.on_pre_process_message(msg(10, "/start qr_abc"), {})), "не подписан: /start остановлен")
    check(SENT and SENT[-1][1] == t("sub_gate"), "показан экран «подпишитесь»")
    kb = SENT[-1][2].inline_keyboard
    check(kb[0][0].url == "https://t.me/yashilqollar" and kb[1][0].callback_data == "check_subscription", "кнопки: канал + «Obuna bo'ldim»")
    check(await L._async.get("sub:start:10") == "qr_abc", "deep-link qr_abc запомнен")
    check(not await passes(mw.on_pre_process_message(msg(10, "📍 Iflos joy"), {})), "не подписан: кнопки меню тоже остановлены")
    check(await L._async.get("sub:start:10") == "qr_abc", "обычный текст не стирает запомненную ссылку")
    check(not await passes(mw.on_pre_process_callback_query(cb(10, "spv:1"), {})), "не подписан: inline-кнопки остановлены")
    check(await passes(mw.on_pre_process_callback_query(cb(10, "check_subscription"), {})), "«Obuna bo'ldim» сам проходит через middleware")
    check(await passes(mw.on_pre_process_message(msg(10, "/start", "supergroup"), {})), "группы не трогаем")

    # язык экрана — русский
    current_lang.set("ru"); SENT.clear()
    await passes(mw.on_pre_process_message(msg(11, "/start"), {}))
    check("Добро пожаловать" in SENT[-1][1] and SENT[-1][2].inline_keyboard[1][0].text == "✅ Я подписался", "экран на языке человека (ru)")
    current_lang.set("uz")

    # «Obuna bo'ldim», но всё ещё не подписан
    SENT.clear(); started = []
    async def fake_user_start(message, state, lang=None, _args=None): started.append((message.from_user.id, _args))
    ST.user_start = fake_user_start
    await H.check_subscription(cb(10, "check_subscription"), dp.current_state(chat=10, user=10))
    check(not started and any(s[0] == "alert" and s[1] == t("sub_not_yet") for s in SENT), "ещё не подписан → «Hali obuna bo'lmagansiz», /start не идёт")

    # подписался → /start продолжается ОТ ИМЕНИ ЧЕЛОВЕКА и со старой ссылкой
    MEMBERS[10] = "member"
    await H.check_subscription(cb(10, "check_subscription"), dp.current_state(chat=10, user=10))
    check(started == [(10, "qr_abc")], "после подписки /start продолжен от человека (не от бота) с qr_abc")
    check(await L._async.get("sub:start:10") is None, "запомненная ссылка удалена")
    check(await L._async.get("sub:ok:10") == "1", "подписка запомнена в кэше")

    # кэш: второй раз Telegram не спрашиваем
    CALLS.clear()
    check(await passes(mw.on_pre_process_message(msg(10, "hi"), {})) and CALLS == [], "подписан: проходит, из кэша без запроса в Telegram")

    # ?start=spot → после подписки сразу «Iflos joy»
    MEMBERS[12] = "left"
    await passes(mw.on_pre_process_message(msg(12, "/start spot"), {}))
    spot = []
    async def fake_spot_start(message, state): spot.append(message.from_user.id)
    SPH.spot_start = fake_spot_start
    MEMBERS[12] = "administrator"
    await H.check_subscription(cb(12, "check_subscription"), dp.current_state(chat=12, user=12))
    check(spot == [12], "start=spot → после подписки сразу форма «Iflos joy»")

    # статусы
    for st, exp in (("creator", True), ("administrator", True), ("member", True), ("left", False), ("kicked", False)):
        MEMBERS[20] = st
        check(await S.is_member(bot, 20) is exp, f"статус {st} → {exp}")
    MEMBERS[20] = "restricted"
    check(await S.is_member(bot, 20) is True, "restricted (в канале) → подписан")

    # сбой проверки — не блокируем
    MEMBERS[30] = exceptions.BadRequest("Chat not found")
    check(await passes(mw.on_pre_process_message(msg(30, "/start"), {})), "бот не админ канала / канал не найден → людей не блокируем")
    MEMBERS[31] = exceptions.NetworkError("timeout")
    check(await passes(mw.on_pre_process_message(msg(31, "/start"), {})), "сеть упала → людей не блокируем")
    MEMBERS[32] = exceptions.BadRequest("User not found")
    check(not await passes(mw.on_pre_process_message(msg(32, "/start"), {})), "User not found → не подписан")
    check(await S.check(bot, 30) and await L._async.get("sub:ok:30") is None, "при сбое ничего не кэшируем")

    # отписался → после истечения кэша снова экран
    await L._async.delete("sub:ok:10"); MEMBERS[10] = "left"
    check(not await passes(mw.on_pre_process_message(msg(10, "hi"), {})), "отписался → снова просит подписаться")

asyncio.get_event_loop().run_until_complete(main())
print(f"OK: {ok} проверок")
