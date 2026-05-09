import qrcode
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from django.utils import timezone
# Импорты по твоей структуре моделей
from app_telegram.models import TGUser, ProjectParticipation, EcoProject 

# ТВОИ АДМИНЫ (ID)
ADMIN_IDS = [7336334074, 998920105472, 998998951002, 998904815816, 998908291932]

# --- ГЕНЕРАЦИЯ QR ---
async def send_user_qr(message: types.Message):
    bot_info = await message.bot.get_me()
    qr_link = f"https://t.me/{bot_info.username}?start=qr_{message.from_user.id}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_link)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    
    await message.answer_photo(
        photo=bio,
        caption="🌿 <b>Sizning shaxsiy eko-kodingiz!</b>\n\nTadbirga kelganingizda adminga ko'rsating."
    )

# --- ЛОГИКА ПРОВЕРКИ ---
@sync_to_async
def process_qr_logic(admin_id, target_tg_id):
    if admin_id not in ADMIN_IDS:
        return "❌ Sizda adminlik huquqi yo'q!"

    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!"

    # УМНЫЙ ПОИСК ПРОЕКТА
    # В моделях у тебя TASHKENT_V и TASHKENT_S. Объединяем их для поиска.
    search_regions = [volunteer.region]
    if volunteer.region in ['tashkent_s', 'tashkent_v']:
        search_regions = ['tashkent_s', 'tashkent_v']

    # Так как в модели DateTimeField, мы ищем проекты, которые начинаются сегодня
    today = timezone.now().date()
    
    project = EcoProject.objects.filter(
        is_active=True, 
        date__date=today, # __date вытаскивает только дату из DateTimeField
        region__in=search_regions
    ).first()

    # Если на сегодня нет, берем ЛЮБОЙ активный проект в этом регионе (для страховки)
    if not project:
        project = EcoProject.objects.filter(
            is_active=True, 
            region__in=search_regions
        ).first()

    if not project:
        region_name = volunteer.get_region_display()
        return f"❌ {region_name}da hozir faol loyiha topilmadi!"

    # Проверка участия
    participation = ProjectParticipation.objects.filter(project=project, user=volunteer).first()
    
    if not participation:
        return f"❌ Foydalanuvchi '{project.title}' loyihasiga ro'yxatdan o'tmagan!"

    if participation.status == 'attended':
        return f"⚠️ {volunteer.fullname} allaqachon tasdiqlangan!"

    # МЕНЯЕМ СТАТУС
    # В твоей модели ProjectParticipation.save() уже прописана логика начисления баллов!
    participation.status = 'attended'
    participation.save() 
    
    return f"✅ <b>Tayyor!</b>\n{volunteer.fullname} kelgani tasdiqlandi.\nБаланс: {volunteer.balance} ball"

# --- ХЕНДЛЕРЫ ---
async def show_qr_handler(message: types.Message):
    await send_user_qr(message)

async def scan_qr_handler(message: types.Message):
    args = message.get_args()
    if not args: return
    
    target_id = args.replace('qr_', '')
    result_text = await process_qr_logic(message.from_user.id, target_id)
    await message.answer(result_text, parse_mode="HTML")
    
    if "✅" in result_text:
        try:
            await message.bot.send_message(
                target_id, 
                "🌟 <b>Rahmat!</b>\nTadbirga kelganingiz tasdiqlandi. 10 ball qo'shildi! 🌿",
                parse_mode="HTML"
            )
        except: pass

def register_qr_handlers(dp: Dispatcher):
    dp.register_message_handler(
        scan_qr_handler, 
        lambda m: m.get_args() and m.get_args().startswith('qr_'), 
        commands=["start"], 
        state="*"
    )
    dp.register_message_handler(
        show_qr_handler, 
        text="🌿 Mening QR-kodim", 
        state="*"
    )