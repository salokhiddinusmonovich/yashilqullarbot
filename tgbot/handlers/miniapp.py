"""
Вход в Mini App из бота: кнопка меню рядом с полем ввода (ставится при
запуске бота), команда /app и кнопка «открыть в приложении» под записью
на мероприятие. Адрес — MINIAPP_URL в .env; без него всё это выключено.
"""
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from tgbot.i18n import t

logger = logging.getLogger(__name__)


def app_url(bot: Bot, **params) -> str | None:
    base = bot["config"].misc.miniapp_url
    if not base:
        return None
    if params:
        base += "/?" + "&".join(f"{k}={v}" for k, v in params.items())
    return base


def open_app_kb(bot: Bot, label_key: str = "btn_open_app", **params) -> InlineKeyboardMarkup | None:
    url = app_url(bot, **params)
    if not url:
        return None
    return InlineKeyboardMarkup().add(InlineKeyboardButton(t(label_key), web_app=WebAppInfo(url=url)))


async def setup_menu_button(bot: Bot):
    url = app_url(bot)
    if not url:
        return
    try:
        await bot.set_chat_menu_button(
            menu_button=types.MenuButtonWebApp(text="🌿 Ilova", web_app=WebAppInfo(url=url))
        )
        logger.info("Mini App menu button set: %s", url)
    except Exception as e:
        logger.warning("Could not set menu button: %s", e)


async def app_command(message: types.Message):
    kb = open_app_kb(message.bot)
    if kb:
        await message.answer(t("app_intro"), reply_markup=kb)


def register_miniapp(dp: Dispatcher):
    dp.register_message_handler(app_command, commands=["app"], state="*")
