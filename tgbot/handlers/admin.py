import asyncio
import logging
from aiogram import types, Dispatcher
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async

# Импортируем твою модель пользователя
from app_telegram.models import TGUser

logger = logging.getLogger(__name__)

# --- 1. СПИСОК АДМИНОВ ---
# Добавь сюда свой ID и ID других админов
ADMINS = [123456789, 987654321]  # <--- ЗАМЕНИ НА СВОЙ ID

async def start_broadcast(message: types.Message):
    """
    Функция рассылки. 
    Инструкция: Пришли фото/текст в бот, нажми 'Ответить' (Reply) на него и напиши /send
    """
    
    # Проверка на админа
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет прав для этой команды. ❌")
        return

    # Проверка, что команда дана в ответ на сообщение
    if not message.reply_to_message:
        await message.answer(
            "<b>Ошибка!</b>\n\nЧтобы сделать рассылку, ответьте командой <code>/send</code> на сообщение, которое хотите разослать.",
            parse_mode="HTML"
        )
        return

    # Берем сообщение, на которое ответил админ
    broadcast_obj = message.reply_to_message
    
    # Получаем список всех пользователей из БД
    users = await sync_to_async(list)(TGUser.objects.all())
    
    await message.answer(f"🚀 <b>Рассылка запущена!</b>\nЦель: {len(users)} пользователей.", parse_mode="HTML")

    count = 0
    blocked_count = 0
    errors = 0

    # Начинаем цикл рассылки
    for user in users:
        try:
            # Метод copy_to идеально копирует любое сообщение (текст, фото, видео, кнопки)
            await broadcast_obj.copy_to(chat_id=user.tg_id)
            count += 1
            
            # Лимит Telegram: не более 30 сообщений в секунду. 
            # Задержка 0.05 сек дает нам ~20 сообщений в секунду — это безопасно.
            await asyncio.sleep(0.05) 

        except exceptions.BotBlocked:
            blocked_count += 1
        except exceptions.ChatNotFound:
            errors += 1
        except exceptions.RetryAfter as e:
            # Если словили лимит — ждем сколько просит Telegram и шлем снова
            await asyncio.sleep(e.timeout)
            await broadcast_obj.copy_to(chat_id=user.tg_id)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при рассылке пользователю {user.tg_id}: {e}")
            errors += 1

    # Финальный отчет
    report = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"👤 Всего пользователей: {len(users)}\n"
        f"📥 Получили: {count}\n"
        f"🚫 Заблокировали бота: {blocked_count}\n"
        f"⚠️ Ошибки: {errors}"
    )
    await message.answer(report, parse_mode="HTML")

# --- РЕГИСТРАЦИЯ ХЕНДЛЕРА ---
def register_admin_handlers(dp: Dispatcher):
    # Команда /send работает во всех состояниях
    dp.register_message_handler(start_broadcast, commands=['send'], state="*")