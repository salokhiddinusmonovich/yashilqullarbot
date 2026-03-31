from aiogram import Bot
from django.conf import settings

async def send_acceptance_msg(chat_id, project):
    bot = Bot(token=settings.BOT_TOKEN)
    text = (
        f"🎉 <b>Tabriklaymiz!</b>\n\n"
        f"Sizning profilingiz tasdiqlandi. <b>{project.title}</b> loyihasiga qabul qilindingiz!\n\n"
        f"📍 Tadbir lokatsiyasi: {project.location_url}\n"
        f"📢 Maxsus kanalimizga qo'shiling:\n{project.channel_link}\n\n"
        f"U yerda barcha muhim ma'lumotlar berib boriladi. Ko'rishguncha! 🌿"
    )
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML")
    finally:
        await (await bot.get_session()).close()