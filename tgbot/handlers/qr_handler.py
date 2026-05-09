import qrcode
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from django.utils import timezone
# Проверь, чтобы путь к моделям был именно таким
from app_telegram.models import TGUser, ProjectParticipation, EcoProject 

# ТВОЙ СПИСОК АДМИНОВ (ID)
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

# --- ЛОГИКА ПРОВЕРКИ (BACKEND) ---
@sync_to_async
def process_qr_logic(admin_id, target_tg_id):
    # 1. Проверка прав админа
    if admin_id not in ADMIN_IDS:
        return "❌ Sizda adminlik huquqi yo'q!"

    # 2. Поиск волонтера
    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!"

    # 3. УМНЫЙ ПОИСК ПРОЕКТА (С учетом Ташкент город/область)
    today = timezone.now().date()
    
    # Список регионов для поиска (объединяем Ташкент город и область)
    # ВАЖНО: Проверь, чтобы эти ключи ('tashkent_s', 'tashkent_v') совпадали с твоим choices в моделях!
    search_regions = [volunteer.region]
    tashkent_variants = ['tashkent_s', 'tashkent_v'] 
    
    if volunteer.region in tashkent_variants:
        search_regions = tashkent_variants

    # Ищем проект: Активный + Сегодня + Регион входит в список
    project = EcoProject.objects.filter(
        is_active=True, 
        date=today, 
        region__in=search_regions
    ).first()

    # Если по дате не нашли, ищем любой активный в этом регионе (на всякий случай)
    if not project:
        project = EcoProject.objects.filter(
            is_active=True, 
            region__in=search_regions
        ).first()

    if not project:
        return f"❌ {volunteer.get_region_display()}da hozir faol loyiha topilmadi!"

    # 4. Проверка регистрации волонтера на этот проект
    participation = ProjectParticipation.objects.filter(project=project, user=volunteer).first()
    
    if not participation:
        return f"❌ Bu foydalanuvchi '{project.title}' loyihasiga ro'yxatdan o'tmagan!"

    if participation.status == 'attended':
        return f"⚠️ {volunteer.fullname} allaqachon tasdiqlangan!"

    # 5. УСПЕХ: Начисляем баллы
    participation.status = 'attended'
    participation.save() # Твой save() в моделях сам начислит баллы
    
    return f"✅ <b>Tayyor!</b>\n{volunteer.fullname} kelgani tasdiqlandi.\nLoyiha: {project.title}"

# --- ХЕНДЛЕРЫ (ИНТЕРФЕЙС) ---

async def show_qr_handler(message: types.Message):
    """Вызывается при нажатии на кнопку в меню"""
    await send_user_qr(message)

async def scan_qr_handler(message: types.Message):
    """Вызывается при сканировании QR (через /start qr_...)"""
    args = message.get_args()
    if not args: return
    
    target_id = args.replace('qr_', '')
    result_text = await process_qr_logic(message.from_user.id, target_id)
    await message.answer(result_text, parse_mode="HTML")
    
    # Уведомление волонтеру
    if "✅" in result_text:
        try:
            await message.bot.send_message(
                target_id, 
                "🌟 <b>Rahmat!</b>\nTadbirga kelganingiz tasdiqlandi. Ballar hisobingizga qo'shildi! 🌿",
                parse_mode="HTML"
            )
        except:
            pass

# --- РЕГИСТРАЦИЯ ---
def register_qr_handlers(dp: Dispatcher):
    # Хендлер сканера (обязательно ПЕРВЫМ)
    dp.register_message_handler(
        scan_qr_handler, 
        lambda m: m.get_args() and m.get_args().startswith('qr_'), 
        commands=["start"], 
        state="*"
    )
    # Хендлер кнопки
    dp.register_message_handler(
        show_qr_handler, 
        text="🌿 Mening QR-kodim", 
        state="*"
    )