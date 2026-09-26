from aiogram import types, Dispatcher

from tgbot.i18n import t, variants


async def shop_pass(message: types.Message):
    await message.answer(t("shop_soon"))


def register_shop(dp: Dispatcher):
    dp.register_message_handler(shop_pass, text=variants("btn_shop"), state="*")
