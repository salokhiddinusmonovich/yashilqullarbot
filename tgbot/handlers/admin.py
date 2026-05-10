import asyncio
import logging
from aiogram import types, Dispatcher
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from app_telegram.models import TGUser

logger = logging.getLogger(__name__)

async def run_broadcast(message: types.Message):
    # 1. Проверка прав через БД (самый надежный способ)
    user_in_db = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    
    # Если юзера нет в БД или у него нет флага is_admin — игнорим
    if not user_in_db or not getattr(user_in_db, 'is_admin', False):
        # Если хочешь, чтобы бот молчал для не-админов, оставь просто return
        # Если хочешь уведомление: await message.answer("❌ Sizda admin huquqi yo'q!")
        return

    # 2. Проверка на Reply
    if not message.reply_to_message:
        await message.answer("ℹ️ <b>Рассылка:</b>\nОтветь командой <code>/send</code> на пост (текст/фото), который нужно разослать всем волонтерам.", parse_mode="HTML")
        return

    # 3. Получаем ВСЕХ юзеров
    all_users = await sync_to_async(list)(TGUser.objects.all())
    
    if not all_users:
        await message.answer("❌ База пользователей пуста.")
        return

    await message.answer(f"🚀 <b>Рассылка запущена!</b>\nПолучателей: {len(all_users)}")

    count = 0
    blocked = 0
    errors = 0

    # 4. Цикл отправки с защитой от Flood
    for user in all_users:
        try:
            await message.reply_to_message.copy_to(chat_id=user.tg_id)
            count += 1
            # Задержка 0.05 сек — критически важна для больших баз (5000+ чел)
            await asyncio.sleep(0.05) 
        except exceptions.BotBlocked:
            blocked += 1
        except exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
            await message.reply_to_message.copy_to(chat_id=user.tg_id)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки на {user.tg_id}: {e}")
            errors += 1

    # 5. Итоговый отчет
    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📥 Получили: {count}\n"
        f"🚫 Блокировок: {blocked}\n"
        f"⚠️ Ошибок: {errors}",
        parse_mode="HTML"
    )

def register_admin(dp: Dispatcher):
    dp.register_message_handler(run_broadcast, commands=['send'], state="*")