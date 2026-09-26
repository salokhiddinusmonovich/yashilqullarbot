"""
Выбор языка: при первом /start (до регистрации), по кнопке
"🌐 Til · Язык · Language" в главном меню и по команде /lang.
"""
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from asgiref.sync import sync_to_async

from tgbot.i18n import t, current_lang, LANG_BUTTON, LANGS
from tgbot.keyboards import reply
from tgbot.services.lang import set_lang


async def ask_language(message: types.Message):
    await message.answer(t("lang_choose"), reply_markup=reply.lang_kb())


async def lang_command(message: types.Message):
    await ask_language(message)


async def lang_chosen(call: types.CallbackQuery, state: FSMContext):
    from app_telegram.models import TGUser
    from .link_account import ask_if_registered

    lang = call.data.split(":", 1)[1]
    if lang not in LANGS:
        await call.answer()
        return
    await set_lang(call.from_user.id, lang)
    current_lang.set(lang)
    await call.answer(t("lang_saved"))
    try:
        await call.message.edit_text(t("lang_saved"))
    except Exception:
        pass

    user = await sync_to_async(TGUser.objects.filter(tg_id=call.from_user.id).only("is_admin").first)()
    if user:
        await call.message.answer(t("main_menu"), reply_markup=reply.hi_there(user.is_admin))
        return

    # Новый человек: язык выбран до регистрации — продолжаем знакомство.
    # Если он уже был посреди регистрации — не сбиваем её.
    if await state.get_state() is None:
        await ask_if_registered(call.message)


def register_language(dp: Dispatcher):
    dp.register_message_handler(lang_command, commands=["lang", "language", "til"], state="*")
    dp.register_message_handler(lang_command, text=LANG_BUTTON, state="*")
    dp.register_callback_query_handler(lang_chosen, lambda c: c.data.startswith("setlang:"), state="*")
