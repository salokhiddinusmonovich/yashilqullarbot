"""🎁 /yakun — итоги года (картинка-сторис + кнопка «открыть историю» в Mini App)."""
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async

from tgbot.i18n import t, current_lang


@sync_to_async
def _user(tg_id: int):
    from app_telegram import wrapped
    from app_telegram.models import TGUser
    u = TGUser.objects.filter(tg_id=tg_id).first()
    return u, (wrapped.year_for(preview=wrapped.can_preview(u)) if u else None)


async def yakun_handler(message: types.Message):
    from tgbot.services.wrapped import send_one
    user, year = await _user(message.from_user.id)
    if not user or not year:
        await message.answer(t("wr_soon"))
        return
    await message.answer(t("adm_preparing"))
    await send_one(message.bot, user, year, current_lang.get() or "uz")


def register_wrapped(dp: Dispatcher):
    dp.register_message_handler(yakun_handler, commands=["yakun", "wrapped", "itogi_goda"], state="*")
