from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from tgbot.models.commands import add_or_create_user
from  ..keyboards import reply
from aiogram.utils.markdown import hbold
from app_telegram.models import TGUser
from asgiref.sync import sync_to_async


async def user_start(message: Message, state: FSMContext):
    await state.finish()   # всегда чистим

    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    # debug: если нужно, логируй:
    # print("user from start:", user, getattr(user, "phone", None))

    if user:
        await message.answer("👋 Salom, ism! @YashilQollar oilasiga xush kelibsiz.", reply_markup=reply.hi_there())
    else:
        await message.answer(f"👋 Salom, ism! @YashilQollar oilasiga xush kelibsiz., {hbold(message.from_user.full_name)}", reply_markup=reply.auth_btn())



def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
