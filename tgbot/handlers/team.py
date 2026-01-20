from aiogram import types
from aiogram.dispatcher import Dispatcher
from asgiref.sync import sync_to_async
from app_telegram.models import TeamMemberYashilQullar
from aiogram.types import InputFile
from PIL import Image
import io
import os


MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 МБ


@sync_to_async
def get_all_team_members():
    return list(
        TeamMemberYashilQullar.objects.select_related('tg_user').all()
    )


def resize_image_for_telegram(path: str) -> io.BytesIO:
    """Сжимает изображение для Telegram (если больше 10 МБ)"""
    img = Image.open(path)
    max_side = 1024  # рекомендуемый размер по большей стороне
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf


async def show_team_all_member(message: types.Message):
    members = await get_all_team_members()

    if not members:
        await message.answer("Jamoa a’zolari hali qo‘shilmagan.")
        return

    for member in members:
        text = (
            f"👤 <b>{member.full_name}</b>\n"
            f"🎓 {member.education or '—'}\n"
            f"🛠 {member.skills or '—'}\n"
            f"💬 {member.motto or '—'}\n"
            f"🔗 @{member.telegram_username}" if member.telegram_username else ""
        )

        if member.image:
            file_size = os.path.getsize(member.image.path)
            if file_size <= MAX_PHOTO_SIZE:
                # отправляем как обычное фото
                await message.answer_photo(
                    photo=InputFile(member.image.path),
                    caption=text,
                    parse_mode="HTML"
                )
            else:
                # сжимаем и отправляем как фото
                buf = resize_image_for_telegram(member.image.path)
                await message.answer_photo(
                    photo=InputFile(buf, filename="member.jpg"),
                    caption=text,
                    parse_mode="HTML"
                )
        else:
            await message.answer(
                text,
                parse_mode="HTML"
            )


def register_team(dp: Dispatcher):
    dp.register_message_handler(
        show_team_all_member,
        lambda m: m.text == "🫂 Loyiha yetakchilari",
        state="*"
    )
