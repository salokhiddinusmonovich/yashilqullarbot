from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async


class FeedbackStates(StatesGroup):
    waiting_for_comment = State()


def rating_keyboard(project_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=5)
    kb.add(*[
        InlineKeyboardButton(text=f"{n}⭐", callback_data=f"fb_rate_{project_id}_{n}")
        for n in range(1, 6)
    ])
    return kb


async def ask_feedback(bot, tg_id: int, project_id: int, project_title: str):
    """
    Вызови эту функцию сразу после того, как волонтёру пришло
    уведомление "Tadbirda ishtirok etganingiz tasdiqlandi" —
    то есть внутри qr_handler.py / process_qr_logic, после успешной
    отметки посещения.
    """
    try:
        await bot.send_message(
            chat_id=tg_id,
            text=(
                f"🙏 <b>{project_title}</b> tadbiri haqida fikringizni bilishni xohlaymiz!\n\n"
                f"Tadbirni 1 dan 5 gacha baholang:"
            ),
            reply_markup=rating_keyboard(project_id),
            parse_mode="HTML"
        )
    except Exception:
        pass  # юзер мог заблокировать бота — не критично, просто пропускаем


async def process_rating_callback(call: types.CallbackQuery, state: FSMContext):
    _, _, project_id, rating = call.data.split("_", 3)
    await state.update_data(project_id=int(project_id), rating=int(rating))
    await FeedbackStates.waiting_for_comment.set()

    await call.message.edit_text(
        f"Rahmat! Siz {rating}⭐ qo'ydingiz.\n\n"
        f"Endi, iltimos, batafsil yozing:\n"
        f"• Nima yoqmadi yoki nima yaxshi bo'lmadi?\n"
        f"• Nimani yaxshilash kerak deb o'ylaysiz?\n\n"
        f"Javobingizni bitta xabar sifatida yuboring 👇"
    )
    await call.answer()


async def process_comment(message: types.Message, state: FSMContext):
    from app_telegram.models import TGUser, EcoProject, EventFeedback

    data = await state.get_data()
    project_id = data.get('project_id')
    rating = data.get('rating')
    await state.finish()

    if not project_id or not rating:
        await message.answer("Xatolik yuz berdi, qaytadan urinib ko'ring.")
        return

    user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    project = await sync_to_async(EcoProject.objects.get)(id=project_id)

    await sync_to_async(EventFeedback.objects.update_or_create)(
        user=user, project=project,
        defaults={'rating': rating, 'comment': message.text}
    )

    await message.answer(
        "✅ Rahmat! Fikringiz uchun tashakkur, bu bizga yaxshilanishga yordam beradi. 🌿"
    )


def register_feedback(dp: Dispatcher):
    dp.register_callback_query_handler(
        process_rating_callback,
        lambda c: c.data and c.data.startswith("fb_rate_"),
        state="*",
    )
    dp.register_message_handler(process_comment, state=FeedbackStates.waiting_for_comment)