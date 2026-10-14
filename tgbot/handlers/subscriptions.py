"""«✅ Я подписался»: проверяем заново (без кэша) и продолжаем — с той же ссылки, с которой человек пришёл."""
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery

from tgbot.i18n import t
from tgbot.services import subscription as sub
from ..keyboards.subscription import subscription_keyboard


async def check_subscription(callback: CallbackQuery, state: FSMContext, lang: str = None):
    if not await sub.check(callback.bot, callback.from_user.id, fresh=True):
        await callback.answer(t("sub_not_yet"), show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=subscription_keyboard())
        except Exception:
            pass
        return

    await callback.answer(t("sub_ok"))
    try:
        await callback.message.delete()
    except Exception:
        pass

    # продолжаем обычный /start ОТ ИМЕНИ ЧЕЛОВЕКА (сообщение с кнопкой — от бота, у него другой from_user)
    from .start import user_start
    from .spots import spot_start
    msg = callback.message
    msg.from_user = callback.from_user
    args = await sub.pop_start(callback.from_user.id)
    if args == "spot":                        # «📍 Iflos joy» из Mini App — у него свой /start (register_spots_start)
        await spot_start(msg, state)
    else:
        await user_start(msg, state, lang=lang, _args=args)


def register_subscription(dp: Dispatcher):
    dp.register_callback_query_handler(check_subscription, lambda c: c.data == "check_subscription", state="*")
