from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from ..keyboards.subscription import subscription_keyboard


CHANNEL_USERNAME = "@yashilqollar"


async def check_subscription(
    callback: CallbackQuery,
    state: FSMContext
):
    user_id = callback.from_user.id

    try:
        member = await callback.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        # Статусы пользователей Telegram
        subscribed = member.status in (
            "creator",
            "administrator",
            "member"
        )

    except Exception:
        subscribed = False

    if not subscribed:
        await callback.answer(
            "❌ Вы ещё не подписались на канал.",
            show_alert=True
        )

        await callback.message.edit_reply_markup(
            reply_markup=subscription_keyboard()
        )
        return

    # Подписка подтверждена
    await callback.answer("✅ Подписка подтверждена!")

    # Получаем сохранённые аргументы /start
    data = await state.get_data()
    start_args = data.get("start_args", "")

    # Убираем старое сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Импортируем здесь, чтобы избежать circular import
    from .start import user_start

    # Продолжаем обычный /start
    await user_start(
        callback.message,
        state,
        _skip_subscription=True,
        _args=start_args
    )


def register_subscription(dp: Dispatcher):
    dp.register_callback_query_handler(
        check_subscription,
        lambda c: c.data == "check_subscription",
        state="*"
    )