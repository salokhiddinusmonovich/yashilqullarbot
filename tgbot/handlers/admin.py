import asyncio
import logging
from aiogram import types, Dispatcher
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async

# Импортируем твою модель пользователя
from app_telegram.models import TGUser

logger = logging.getLogger(__name__)

ADMIN_IDS = [7336334074, 998920105472, 998998951002, 998904815816, 998908291932]

async def run_broadcast(message: types.Message):
    """
    Рассылка только для пользователей с галочкой is_tester=True
    """
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.reply_to_message:
        await message.answer("Ответь командой /send на пост, который хочешь затестить!")
        return

    # Берем только тех, у кого стоит галочка "is_tester"
    # testers = await sync_to_async(list)(TGUser.objects.filter(is_tester=True))

    # Берем ВСЕХ пользователей из базы данных
    testers = await sync_to_async(list)(TGUser.objects.all())
    
    if not testers:
        await message.answer("В базе нет пользователей с галочкой is_tester=True!")
        return

    await message.answer(f"🧪 Режим песочницы: шлем сообщение {len(testers)} тестерам...")

    for user in testers:
        try:
            await message.reply_to_message.copy_to(chat_id=user.tg_id)
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"Ошибка на тестере {user.tg_id}: {e}")

    await message.answer("✅ Тестовая рассылка завершена!")

# ИМЯ ФУНКЦИИ ДОЛЖНО БЫТЬ ТАКИМ, КАК В bot.py
def register_admin(dp: Dispatcher):
    dp.register_message_handler(run_broadcast, commands=['send'], state="*")