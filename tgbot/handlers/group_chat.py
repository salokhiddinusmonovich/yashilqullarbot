"""
💬 Ассистент в группах (по умолчанию — @yashilqollarchat): отвечает на вопросы людям прямо в чате.

Когда отвечает:
  • бота упомянули (@yashilqollarbot …) или ответили на его сообщение — всегда;
  • вопрос со знаком «?» (от 3 слов) — если GROUP_AI_MODE=questions (по умолчанию);
  • похоже на вопрос и без «?» (qachon/qayerda/…mi, когда/где/как/есть ли, when/how…) — ИИ сам решает:
    вопрос к нам → отвечает, болтовня людей между собой → «SKIP», бот молчит.
    Чтобы бот ВИДЕЛ обычные сообщения группы: @BotFather → /setprivacy → Disable (или сделать бота админом).
Только в разрешённых группах (GROUP_AI_CHATS: username или id через запятую) — в чужой группе молчит.
Анти-спам: одному человеку — не чаще раза в USER_COOLDOWN c, на группу — не больше CHAT_HOURLY ответов в час.
Стиль — tgbot/services/ai.py: _GROUP_SYSTEM. Этот хендлер регистрируется ПЕРВЫМ и забирает все сообщения
групп, чтобы меню/кнопки/FAQ личного чата в группе не срабатывали.
"""
import logging
import os
import re
import time

from aiogram import Dispatcher, types

from tgbot.services import ai, faq
from tgbot.services.lang import _aclient

log = logging.getLogger(__name__)

ALLOWED = {x.strip().lstrip("@").lower() for x in os.environ.get("GROUP_AI_CHATS", "yashilqollarchat").split(",") if x.strip()}
MODE = os.environ.get("GROUP_AI_MODE", "questions").strip().lower()      # questions | mention
USER_COOLDOWN = int(os.environ.get("GROUP_AI_USER_COOLDOWN", "20"))
CHAT_HOURLY = int(os.environ.get("GROUP_AI_CHAT_HOURLY", "60"))
SERVICE_TG = 777000
# 😎 стикеры: паки через запятую (t.me/addstickers/<ИМЯ> → ИМЯ). ИИ пишет «STICKER:😂» — шлём стикер с этим эмодзи.
STICKER_SETS = [x.strip().split("/")[-1] for x in os.environ.get("GROUP_STICKER_SETS", "MemesMusa").split(",") if x.strip()]
STICKER_GAP = int(os.environ.get("GROUP_STICKER_GAP", "90"))             # не чаще одного стикера на группу за N c
REACTIONS = {"👍", "🔥", "😁", "🤣", "💯", "👏", "🤝", "😎", "🫡", "❤", "🎉", "🤔", "👀", "🙏"}
_TAG = re.compile(r"^\s*(REACT|STICKER)\s*:\s*(\S+)\s*$", re.I | re.M)
_stickers = {}                                                         # «Telegram»: автопересылка постов канала

_me = {}


async def _bot_me(bot):
    if "u" not in _me:
        _me["u"] = await bot.get_me()
    return _me["u"]


def allowed(chat: types.Chat) -> bool:
    return (chat.username or "").lower() in ALLOWED or str(chat.id) in ALLOWED


# слова-вопросы: узбекский (латиница/кириллица), русский, английский
Q_WORDS = {
    "qachon", "qayerda", "qayerga", "qayer", "qanday", "qanaqa", "qancha", "nechta", "necha", "nima", "nimaga", "nega", "kim", "kimga",
    "qaysi", "nimalar", "qachongacha", "қачон", "қаерда", "қандай", "қанча", "нечта", "нима", "нега", "ким", "қайси",
    "когда", "где", "куда", "как", "какой", "какая", "какие", "что", "почему", "зачем", "кто", "сколько", "можно", "есть", "подскажите",
    "скажите", "объясните", "when", "where", "how", "what", "why", "who", "which", "can", "could", "is", "are", "does", "do",
}
_W = re.compile(r"[\w'ʻʼ‘’]+", re.U)


def _is_question(text: str) -> bool:
    """Явный вопрос: со знаком «?» (от 3 слов)."""
    return text.rstrip().endswith("?") and len(_W.findall(text)) >= 3


def _maybe_question(text: str) -> bool:
    """Похоже на вопрос без «?»: «когда будет у вас ещё event», «tadbir qachon bo'ladi», «sertifikat bormi»."""
    words = [w.lower().replace("ʻ", "'").replace("ʼ", "'").replace("‘", "'").replace("’", "'") for w in _W.findall(text)]
    if len(words) < 3:
        return False
    return (any(w in Q_WORDS for w in words)
            or any(len(w) > 4 and w.endswith(("mi", "мi", "ми")) for w in words)      # uz: bormi, bo'ladimi, mumkinmi
            or "ли" in words)


async def _rate_ok(chat_id: int, user_id: int) -> bool:
    try:
        r = _aclient()
        if not await r.set(f"gai:u:{chat_id}:{user_id}", 1, ex=USER_COOLDOWN, nx=True):
            return False
        key = f"gai:c:{chat_id}:{int(time.time() // 3600)}"
        n = await r.incr(key)
        await r.expire(key, 3700)
        return n <= CHAT_HOURLY
    except Exception:
        return True                       # Redis недоступен — не молчим из-за него


def split_tags(answer: str) -> tuple[str, str, str]:
    """«ответ\nREACT:🔥\nSTICKER:😂» → (ответ, реакция, эмодзи стикера)."""
    react = sticker = ""
    for kind, emo in _TAG.findall(answer):
        if kind.upper() == "REACT":
            react = emo
        else:
            sticker = emo
    return _TAG.sub("", answer).strip(), react, sticker


async def _sticker_for(bot, emoji: str) -> str | None:
    import random
    if "all" not in _stickers:
        files = []
        for name in STICKER_SETS:
            try:
                st = await bot.get_sticker_set(name)
                files += [(x.emoji or "", x.file_id) for x in st.stickers]
            except Exception as e:
                log.warning("sticker set %s: %s", name, e)
        _stickers["all"] = files
    files = _stickers["all"]
    if not files:
        return None
    same = [f for e, f in files if emoji and emoji.strip("\ufe0f") in e]
    return random.choice(same or [f for _, f in files])


async def _fun(message: types.Message, react: str, sticker: str):
    if react and react.strip("\ufe0f") in {r.strip("\ufe0f") for r in REACTIONS}:
        try:      # setMessageReaction — в aiogram 2 нет метода, зовём Bot API напрямую
            import json
            await message.bot.request("setMessageReaction", {"chat_id": message.chat.id, "message_id": message.message_id,
                                                             "reaction": json.dumps([{"type": "emoji", "emoji": react}], ensure_ascii=False)})
        except Exception as e:
            log.warning("reaction: %s", e)
    if sticker and STICKER_SETS:
        try:
            if await _aclient().set(f"gai:st:{message.chat.id}", 1, ex=STICKER_GAP, nx=True):
                fid = await _sticker_for(message.bot, sticker)
                if fid:
                    await message.bot.send_sticker(message.chat.id, fid)
        except Exception as e:
            log.warning("sticker: %s", e)


async def group_message(message: types.Message):
    if not allowed(message.chat) or not message.from_user or message.from_user.is_bot:
        return
    if message.from_user.id == SERVICE_TG or message.sender_chat or getattr(message, "is_automatic_forward", False):
        return                            # пост канала в обсуждениях / сообщение от имени канала
    text = (message.text or message.caption or "").strip()
    if not text or text.startswith("/"):
        return
    me = await _bot_me(message.bot)
    tag = f"@{me.username}".lower()
    mentioned = tag in text.lower()
    reply_to_bot = bool(message.reply_to_message and message.reply_to_message.from_user
                        and message.reply_to_message.from_user.id == me.id)
    explicit = mentioned or reply_to_bot or (MODE == "questions" and _is_question(text))
    maybe = not explicit and MODE == "questions" and _maybe_question(text)
    if not (explicit or maybe):
        return
    question = re.sub(re.escape(tag), "", text, flags=re.I).strip(" ,:—-") or text
    if not await _rate_ok(message.chat.id, message.from_user.id):
        return
    # на что человек отвечает — даём как контекст (своё прошлое сообщение бота или реплику собеседника)
    context = ""
    if message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
        who = "bot (you)" if reply_to_bot else (message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else "someone")
        context = f"{who}: {(message.reply_to_message.text or message.reply_to_message.caption)[:600]}"
    if ai.enabled():
        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
            answer = await ai.group_answer(question, message.from_user.first_name or "", context, allow_skip=maybe)
            if answer:                    # пусто = ИИ решил, что это болтовня, а не вопрос к нам
                text_out, react, sticker = split_tags(answer)
                if text_out:
                    await message.reply(text_out, disable_web_page_preview=True)
                await _fun(message, react, sticker)
            return
        except ai.Unavailable as e:
            log.warning("group ai unavailable: %s | %s", e, ai.LAST_ERROR)
        except Exception:
            log.exception("group ai")
    # ИИ недоступен: на прямое обращение — готовый ответ из справочника или честное «позже»; на просто «?» — молчим
    if explicit and (mentioned or reply_to_bot):
        entry = faq.match(question)
        if entry:
            await message.reply(faq.answer(entry, "uz"))
        else:
            await message.reply("😅 Hozir AI biroz dam olyapti — savolni @yashilqollarbot'ga yozing yoki birozdan keyin qayta so'rang.")


def register_group_chat(dp: Dispatcher):
    # ПЕРВЫМ: всё из групп забираем сюда (иначе сработали бы меню и FAQ личного чата)
    dp.register_message_handler(group_message, chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
                                content_types=types.ContentTypes.ANY, state="*")
