"""
Короткая инструкция "как пользоваться ботом" — для волонтёров и
отдельно для координаторов (всех ролей кроме volunteer).
Показывается после регистрации/привязки и по кнопке "❓" / /help.
"""
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async

from tgbot.i18n import t, variants


@sync_to_async
def _is_staff(tg_id: int) -> bool:
    """Инструкция для координаторов — по роли, как и сам сканер (services.is_staff)."""
    from app_telegram.models import TGUser
    from app_telegram.services import is_staff
    return is_staff(TGUser.objects.filter(tg_id=tg_id).only("role", "is_admin").first())


async def send_guide(message: types.Message, tg_id: int = None):
    text = t("guide_volunteer")
    if await _is_staff(tg_id or message.chat.id):
        text += t("guide_coordinator")
    from .assistant import ask_inline
    await message.answer(text, reply_markup=ask_inline())


async def help_handler(message: types.Message):
    await send_guide(message, message.from_user.id)


def register_help(dp: Dispatcher):
    dp.register_message_handler(help_handler, commands=["help"], state="*")
    dp.register_message_handler(help_handler, text=variants("btn_guide"), state="*")
