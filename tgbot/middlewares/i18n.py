from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
from asgiref.sync import sync_to_async

from tgbot.i18n import current_lang, lang_from_telegram, DEFAULT_LANG
from tgbot.services.lang import get_lang, set_lang


@sync_to_async
def _is_registered(tg_id: int) -> bool:
    from app_telegram.models import TGUser
    return TGUser.objects.filter(tg_id=tg_id).exists()


class I18nMiddleware(BaseMiddleware):
    """
    Выставляет язык текущего юзера — после этого t("...") в хендлерах
    сам отвечает на нужном языке. Хендлер может также принять аргумент
    `lang` (None — если человек новый и язык ещё не выбирал).

    Кто зарегистрировался ДО появления переводов — остаётся на узбекском
    (как и было), без лишнего вопроса. Один раз проверяем по БД и
    запоминаем в Redis, дальше без запросов.
    """

    async def _setup(self, user: types.User, data: dict):
        lang = await get_lang(user.id)
        if lang is None and await _is_registered(user.id):
            lang = DEFAULT_LANG
            await set_lang(user.id, lang)
        data["lang"] = lang
        current_lang.set(lang or lang_from_telegram(user.language_code))

    async def on_pre_process_message(self, message: types.Message, data: dict):
        await self._setup(message.from_user, data)

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        await self._setup(call.from_user, data)
