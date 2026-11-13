"""
📢 Бот работает только для подписчиков канала @yashilqollar.

Любое сообщение / кнопка / команда в личке: не подписан → экран «подпишитесь» и дальше не идём.
Пришёл по ссылке /start <аргументы> — запоминаем их, после «✅ Я подписался» продолжаем с того же места
(tgbot/handlers/subscriptions.py). Группы и каналы не трогаем. Сбой проверки — не блокируем.
"""
from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

from tgbot.keyboards.subscription import subscription_keyboard
from tgbot.i18n import t
from tgbot.services import subscription as sub

CHECK_CALLBACK = "check_subscription"


class SubscriptionMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.type != types.ChatType.PRIVATE or not message.from_user or message.from_user.is_bot:
            return
        if await sub.check(message.bot, message.from_user.id):
            return
        # запоминаем только ссылку С аргументом: повторный пустой /start не должен стереть ref_/qr_/login_
        if message.text and message.text.startswith("/start") and message.get_args():
            await sub.remember_start(message.from_user.id, message.get_args())
        await message.answer(t("sub_gate"), reply_markup=subscription_keyboard())
        raise CancelHandler()

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        if call.data == CHECK_CALLBACK or not call.message or call.message.chat.type != types.ChatType.PRIVATE:
            return
        if await sub.check(call.bot, call.from_user.id):
            return
        await call.answer(t("sub_need"), show_alert=True)
        await call.message.answer(t("sub_gate"), reply_markup=subscription_keyboard())
        raise CancelHandler()
