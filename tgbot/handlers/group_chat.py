"""
💬 Ассистент в группах (по умолчанию — @yashilqollarchat): отвечает на вопросы людям прямо в чате.

Когда отвечает:
  • бота упомянули (@yashilqollarbot …) или ответили на его сообщение — всегда;
  • вопрос со знаком «?» (от 3 слов) — если GROUP_AI_MODE=questions (по умолчанию).
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
SERVICE_TG = 777000                                                         # «Telegram»: автопересылка постов канала

_me = {}


async def _bot_me(bot):
    if "u" not in _me:
        _me["u"] = await bot.get_me()
    return _me["u"]


def allowed(chat: types.Chat) -> bool:
    return (chat.username or "").lower() in ALLOWED or str(chat.id) in ALLOWED


def _is_question(text: str) -> bool:
    return text.rstrip().endswith("?") and len(re.findall(r"\w+", text)) >= 3


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
    if not (mentioned or reply_to_bot or (MODE == "questions" and _is_question(text))):
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
            answer = await ai.group_answer(question, message.from_user.first_name or "", context)
            await message.reply(answer, disable_web_page_preview=True)
            return
        except ai.Unavailable as e:
            log.warning("group ai unavailable: %s | %s", e, ai.LAST_ERROR)
        except Exception:
            log.exception("group ai")
    # ИИ недоступен: на прямое обращение — готовый ответ из справочника или честное «позже»; на просто «?» — молчим
    if mentioned or reply_to_bot:
        entry = faq.match(question)
        if entry:
            await message.reply(faq.answer(entry, "uz"))
        else:
            await message.reply("😅 Hozir AI biroz dam olyapti — savolni @yashilqollarbot'ga yozing yoki birozdan keyin qayta so'rang.")


def register_group_chat(dp: Dispatcher):
    # ПЕРВЫМ: всё из групп забираем сюда (иначе сработали бы меню и FAQ личного чата)
    dp.register_message_handler(group_message, chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP],
                                content_types=types.ContentTypes.ANY, state="*")
