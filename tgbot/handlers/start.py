from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message
from tgbot.models.commands import add_or_create_user
from  ..keyboards import reply
from aiogram.utils.markdown import hbold
from app_telegram.models import TGUser
from asgiref.sync import sync_to_async


async def user_start(message: Message, state: FSMContext):
    await state.finish()  # Har doim holatni tozalaymiz

    # Foydalanuvchini bazadan qidiramiz
    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()

    if user:
        # Ro'yxatdan o'tgan bo'lsa, bazadagi fullname ni ko'rsatamiz
        await message.answer(
            f"👋 Salom, {hbold(user.fullname)}! @YashilQollar oilasiga xush kelibsiz.", 
            reply_markup=reply.hi_there()
        )
    else:
        # Ro'yxatdan o'tmagan bo'lsa, Telegramdagi ismini ko'rsatamiz
        await message.answer(
            f"👋 Salom, {hbold(message.from_user.full_name)}! @YashilQollar oilasiga xush kelibsiz.", 
            reply_markup=reply.auth_btn()
        )


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
