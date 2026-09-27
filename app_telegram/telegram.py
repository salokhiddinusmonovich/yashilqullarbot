"""
Отправка сообщений в Telegram из Django (админка, Mini App API).
Бот живёт в отдельном процессе, поэтому здесь своя лёгкая сессия.
"""
import asyncio
import logging
import threading

import requests
from aiogram import Bot
from django.conf import settings
from django.db import close_old_connections

logger = logging.getLogger(__name__)

BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
CHANNEL = "@yashilqollar"


async def _send_many(messages_: list):
    """[(tg_id, text), ...] через ОДНУ сессию бота. Возвращает доставленные tg_id."""
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    delivered = []
    try:
        for tg_id, text in messages_:
            try:
                await bot.send_message(tg_id, text)
                delivered.append(tg_id)
            except Exception as e:
                logger.warning("Telegram send to %s failed: %s", tg_id, e)
            await asyncio.sleep(0.05)  # ~20/сек, ниже лимита Telegram
    finally:
        await (await bot.get_session()).close()
    return delivered


def send_in_background(messages_: list, on_done=None):
    """
    Рассылка в фоновом потоке — HTTP-ответ уходит сразу, не ждём Telegram.
    on_done(delivered_ids) вызывается в том же фоновом потоке.
    """
    def run():
        try:
            delivered = asyncio.run(_send_many(messages_))
            if on_done:
                on_done(delivered)
        except Exception:
            logger.exception("Background send failed")
        finally:
            close_old_connections()

    threading.Thread(target=run, daemon=True).start()


async def _send_docs(docs: list):
    """[(tg_id, bytes, filename, caption), ...] — документы одной сессией бота."""
    from aiogram.types import InputFile
    from io import BytesIO
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    delivered = []
    try:
        for tg_id, data, fname, caption in docs:
            try:
                await bot.send_document(tg_id, InputFile(BytesIO(data), filename=fname), caption=caption)
                delivered.append(tg_id)
            except Exception as e:
                logger.warning("Telegram doc to %s failed: %s", tg_id, e)
            await asyncio.sleep(0.1)
    finally:
        await (await bot.get_session()).close()
    return delivered


def send_documents_in_background(docs: list, on_done=None):
    """Как send_in_background, только файлы. docs — список (tg_id, bytes, filename, caption) или функция, которая его вернёт."""
    def run():
        try:
            items = docs() if callable(docs) else docs
            delivered = asyncio.run(_send_docs(items))
            if on_done:
                on_done(delivered)
        except Exception:
            logger.exception("Background docs failed")
        finally:
            close_old_connections()

    threading.Thread(target=run, daemon=True).start()


def is_channel_member(tg_id: int) -> bool:
    """Подписан ли на канал. При сбое Telegram — не блокируем (True), как и в боте."""
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember",
            params={"chat_id": CHANNEL, "user_id": tg_id}, timeout=4,
        )
        data = r.json()
        if not data.get("ok"):
            return True
        return data["result"]["status"] in ("creator", "administrator", "member")
    except Exception as e:
        logger.warning("getChatMember failed: %s", e)
        return True
