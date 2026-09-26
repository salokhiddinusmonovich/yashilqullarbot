import asyncio

from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware

from tgbot.services import stats


class ActivityMiddleware(BaseMiddleware):
    """
    Отмечает юзера активным за сегодня — для ежедневного отчёта админам.
    В фоне (create_task), чтобы запрос в Redis не задерживал ответ юзеру.
    """

    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.type == types.ChatType.PRIVATE:
            asyncio.create_task(stats.mark_active(message.from_user.id))

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        asyncio.create_task(stats.mark_active(call.from_user.id))
