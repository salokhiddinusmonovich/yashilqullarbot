from aiogram import types
from asgiref.sync import sync_to_async
from aiogram import Dispatcher
from app_telegram.models import TGUser, TeamMemberYashilQullar

async def show_profile(message: types.Message):
    # Получаем пользователя по tg_id
    try:
        user = await sync_to_async(TGUser.objects.get)(tg_id=message.from_user.id)
    except TGUser.DoesNotExist:
        await message.answer("Siz hali ro‘yxatdan o‘tmagansiz. /register orqali ro‘yxatdan o‘ting.")
        return

    # Формируем текст профиля
    profile_text = (
        f"👤 {user.fullname}\n"
        f"• Yoshingiz: {user.age or 'Ko‘rsatilmagan'}\n"
        f"• Email: {user.email}\n"
        f"• Telefon: {user.phone}\n"
        f"• Hudud: {user.region or 'Ko‘rsatilmagan'}\n"
        f"• O‘qish joyi: {user.education_place or 'Ko‘rsatilmagan'}\n"
        f"• Ro‘yxatdan o‘tgan: {user.created.strftime('%d.%m.%Y')}\n"
    )

    # # Если есть связанный TeamMemberYashilQullar, добавляем инфо
    # try:
    #     team_member = await sync_to_async(lambda: user.team_member)()
    #     profile_text += (
    #         f"\n🛠 To‘liq ism: {team_member.full_name}\n"
    #         f"🎓 Ta’lim: {team_member.education or 'Ko‘rsatilmagan'}\n"
    #         f"💡 Ko‘nikmalar: {team_member.skills or 'Ko‘rsatilmagan'}\n"
    #         f"🌐 Telegram username: {team_member.telegram_username or 'Ko‘rsatilmagan'}\n"
    #         f"🏷 Shior: {team_member.motto or 'Ko‘rsatilmagan'}\n"
    #     )
    # except TeamMemberYashilQullar.DoesNotExist:
    #     pass  # если нет связанного TeamMember, просто пропускаем

    await message.answer(profile_text)



def register_profile(dp: Dispatcher):
    dp.register_message_handler(
    show_profile,
    lambda m: m.text == "Mening profilim",
    state="*"
)