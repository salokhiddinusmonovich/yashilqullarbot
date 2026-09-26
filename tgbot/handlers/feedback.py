from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from html import escape

from tgbot.i18n import t
from tgbot.services.lang import lang_of, langs_of
from ..keyboards import reply
from ..keyboards.known_buttons import is_menu_button_text


class FeedbackStates(StatesGroup):
    waiting_for_comment = State()


def rating_keyboard(project_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=5)
    kb.add(*[
        InlineKeyboardButton(text=f"{n}⭐", callback_data=f"fb_rate_{project_id}_{n}")
        for n in range(1, 6)
    ])
    return kb


def skip_comment_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text=t("btn_skip"), callback_data="fb_skip_comment"))
    return kb


async def ask_feedback(bot, tg_id: int, project_id: int, project_title: str):
    """
    Вызывается сразу после подтверждения посещения через QR.
    """
    try:
        await bot.send_message(
            chat_id=tg_id,
            text=t("fb_ask", await lang_of(tg_id), title=escape(project_title)),
            reply_markup=rating_keyboard(project_id),
            parse_mode="HTML"
        )
    except Exception:
        pass


async def process_rating_callback(call: types.CallbackQuery, state: FSMContext):
    _, _, project_id, rating = call.data.split("_", 3)
    await state.update_data(project_id=int(project_id), rating=int(rating))
    await FeedbackStates.waiting_for_comment.set()

    await call.message.edit_text(t("fb_ask_comment", rating=rating), reply_markup=skip_comment_keyboard())
    await call.answer()


async def _save_feedback_and_notify(bot, tg_id: int, project_id: int, rating: int, comment: str):
    """
    Общая часть для «написал комментарий» и «нажал скип» — сохраняет
    фидбек и шлёт уведомление админам. comment может быть пустой строкой,
    если юзер решил не писать ничего.
    """
    from app_telegram.models import TGUser, EcoProject, EventFeedback

    user = await sync_to_async(TGUser.objects.get)(tg_id=tg_id)
    project = await sync_to_async(EcoProject.objects.get)(id=project_id)

    await sync_to_async(EventFeedback.objects.update_or_create)(
        user=user, project=project,
        defaults={'rating': rating, 'comment': comment}
    )

    admin_ids = await sync_to_async(list)(
        TGUser.objects.filter(is_admin=True, tg_id__isnull=False).values_list("tg_id", flat=True)
    )
    langs = await langs_of(admin_ids)

    for admin_id in admin_ids:
        lang = langs.get(admin_id)
        admin_text = t(
            "adm_new_feedback", lang,
            name=escape(user.fullname or "—"),
            uname=f"@{user.username}" if user.username else "—",
            project=escape(project.title),
            stars="⭐" * rating,
            rating=rating,
            comment=escape(comment) if comment else t("fb_no_comment", lang),
        )
        try:
            await bot.send_message(chat_id=admin_id, text=admin_text)
        except Exception:
            pass


async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    project_id = data.get('project_id')
    rating = data.get('rating')

    if not project_id or not rating:
        await state.finish()
        await message.answer(t("error_retry"))
        return

    # ИСПРАВЛЕНО: раньше ЛЮБОЙ текст здесь сохранялся как комментарий —
    # включая нажатие обычной кнопки меню (например, "🌱 Tadbirlar" или
    # "⬅️ Orqaga"), потому что кнопка тоже приходит как обычное текстовое
    # сообщение. Юзер тыкал кнопку меню, а бот молча сохранял её текст как
    # "комментарий" и говорил "спасибо за отзыв" — сама кнопка при этом
    # никак не срабатывала, и юзер оставался как будто в никуда. Теперь
    # такой текст распознаётся как "юзер хочет уйти из фидбека, а не писать
    # комментарий" — сохраняем оценку без комментария и возвращаем меню.
    if is_menu_button_text(message.text):
        await state.finish()
        await _save_feedback_and_notify(message.bot, message.from_user.id, project_id, rating, comment="")
        await message.answer(t("fb_thanks_nocomment"), reply_markup=await reply.main_menu(message.from_user.id))
        return

    await state.finish()
    await _save_feedback_and_notify(message.bot, message.from_user.id, project_id, rating, comment=message.text)
    await message.answer(t("fb_thanks"))


async def process_skip_comment(call: types.CallbackQuery, state: FSMContext):
    """Явная кнопка «⏭ O'tkazib yuborish» рядом с просьбой написать комментарий."""
    data = await state.get_data()
    project_id = data.get('project_id')
    rating = data.get('rating')
    await state.finish()

    if not project_id or not rating:
        await call.answer()
        await call.message.edit_text(t("error_retry"))
        return

    await _save_feedback_and_notify(call.bot, call.from_user.id, project_id, rating, comment="")
    await call.message.edit_text(t("fb_thanks_short"))
    await call.answer()


def register_feedback(dp: Dispatcher):
    dp.register_callback_query_handler(
        process_rating_callback,
        lambda c: c.data and c.data.startswith("fb_rate_"),
        state="*",
    )
    dp.register_callback_query_handler(
        process_skip_comment,
        lambda c: c.data == "fb_skip_comment",
        state="*",
    )
    dp.register_message_handler(process_comment, state=FeedbackStates.waiting_for_comment)
