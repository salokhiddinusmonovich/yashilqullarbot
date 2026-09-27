"""«👥 Пригласи друга» — /invite и кнопка в меню. Логика бонуса — app_telegram/referrals.py."""
from urllib.parse import quote

from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async

from tgbot.i18n import t, variants


async def invite_handler(message: types.Message):
    from app_telegram import referrals
    bot_info = await message.bot.me
    link = referrals.link(bot_info.username, message.from_user.id)
    st = await sync_to_async(referrals.stats)(message.from_user.id)
    share = f"https://t.me/share/url?url={quote(link)}&text={quote(t('invite_share_text'))}"
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton(t("invite_btn_share"), url=share))
    await message.answer(
        t("invite_text", link=link, bonus=st["bonus"], invited=st["invited"], joined=st["joined"], earned=st["joined"] * st["bonus"]),
        reply_markup=kb, disable_web_page_preview=True,
    )


def register_invite(dp: Dispatcher):
    dp.register_message_handler(invite_handler, commands=["invite"], state="*")
    dp.register_message_handler(invite_handler, text=variants("btn_invite"), state="*")
