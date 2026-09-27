"""📅 Дайджест: «🔕 Отключить» в сообщении и /digest — включить/выключить."""
from aiogram import types, Dispatcher

from tgbot.i18n import t
from tgbot.services.lang import _aclient


async def digest_off(call: types.CallbackQuery):
    try:
        await _aclient().sadd("digest:off", call.from_user.id)
    except Exception:
        pass
    await call.answer()
    await call.message.answer(t("digest_off_done"))


async def digest_toggle(message: types.Message):
    r = _aclient()
    try:
        if await r.sismember("digest:off", message.from_user.id):
            await r.srem("digest:off", message.from_user.id)
            await message.answer(t("digest_on_done"))
        else:
            await r.sadd("digest:off", message.from_user.id)
            await message.answer(t("digest_off_done"))
    except Exception:
        await message.answer(t("error_retry"))


def register_digest(dp: Dispatcher):
    dp.register_callback_query_handler(digest_off, text="digest:off", state="*")
    dp.register_message_handler(digest_toggle, commands=["digest", "dayjest", "дайджест"], state="*")
