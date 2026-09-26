from aiogram import Dispatcher
from aiogram.types import Message

from tgbot.i18n import t, variants


async def join_project(message: Message):
    await message.answer(t("join_text"))


def register_project_handlers(dp: Dispatcher):
    dp.register_message_handler(join_project, text=variants("btn_join"), state="*")
