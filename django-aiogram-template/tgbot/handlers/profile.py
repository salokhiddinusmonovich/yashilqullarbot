from aiogram import types
from asgiref.sync import sync_to_async
from aiogram import Dispatcher
from app_telegram.models import TGUser, TeamMemberYashilQullar

async def show_profile(message: types.Message):
    # Foydalanuvchini bazadan qidiramiz
    try:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    except TGUser.DoesNotExist:
        await message.answer("Siz hali ro‘yxatdan o‘tmagansiz. Ro‘yxatdan o‘tish tugmasini bosing.")
        return

    # Profil ma'lumotlarini shakllantiramiz
    profile_text = (
        f" 👤 <b>{user.fullname}</b>\n"
        f"• Yosh: {user.age or '—'}\n"
        f"• Hudud: {user.region}\n"
        f"• O‘qish joyi: {user.education_place or '—'}\n"
        f"• Email: {user.email}\n"
        f"• Telefon: {user.phone}\n"
    
    )

    # Agar foydalanuvchining rasmi bo'lsa
    if user.photo:
        try:
            # Django ImageField obyektining path'idan foydalanamiz
            photo = types.InputFile(user.photo.path)
            await message.answer_photo(
                photo=photo,
                caption=profile_text,
                parse_mode="HTML"
            )
        except Exception:
            # Agar fayl serverda topilmasa, rasmisiz yuboramiz
            await message.answer(profile_text, parse_mode="HTML")
    else:
        # Rasm bo'lmasa matnning o'zini yuboramiz
        await message.answer(profile_text, parse_mode="HTML")

def register_profile(dp: Dispatcher):
    dp.register_message_handler(
        show_profile,
        lambda m: m.text == "👤 Mening profilim",
        state="*"
    )