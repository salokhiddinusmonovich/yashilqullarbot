import qrcode
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from django.utils import timezone

# Импортируем твои модели (убедись, что путь app_telegram правильный)
from app_telegram.models import TGUser, ProjectParticipation, EcoProject 

# ТВОИ АДМИНЫ (ID)
ADMIN_IDS = [7336334074, 998920105472, 998998951002, 998904815816, 998908291932]

# --- 1. ГЕНЕРАЦИЯ QR ---
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

# --- 2. ЛОГИКА БД (ОТДЕЛЬНО) ---
@sync_to_async
def process_qr_logic(admin_id, target_tg_id):
    # Проверка админа
    if admin_id not in ADMIN_IDS:
        return "❌ Sizda adminlik huquqi yo'q!", None

    # Поиск волонтера
    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!", None

    # Объединяем Ташкент город и область
    search_regions = [volunteer.region]
    if volunteer.region in ['tashkent_s', 'tashkent_v']:
        search_regions = ['tashkent_s', 'tashkent_v']

    today = timezone.now().date()
    
    # Ищем проект (учитываем, что в модели DateTimeField через __date)
    project = EcoProject.objects.filter(
        is_active=True, 
        date__date=today, 
        region__in=search_regions
    ).first()

    # Если на сегодня нет, берем просто активный в регионе
    if not project:
        project = EcoProject.objects.filter(
            is_active=True, 
            region__in=search_regions
        ).first()

    if not project:
        return f"❌ {volunteer.get_region_display()}da faol loyiha topilmadi!", None

    # Проверка регистрации
    participation = ProjectParticipation.objects.filter(project=project, user=volunteer).first()
    if not participation:
        return f"❌ Волонтер '{project.title}' лойиҳасига рўйхатдан ўтмаган!", None

    if participation.status == 'attended':
        return f"⚠️ {volunteer.fullname} аллақачон тасдиқланган!", volunteer

    # СОХРАНЕНИЕ
    participation.status = 'attended'
    participation.save() # Здесь срабатывает твой метод в моделях для +10 баллов
    
    # Обновляем данные волонтера из базы, чтобы увидеть новый баланс
    volunteer.refresh_from_db()
    
    success_text = (
        f"✅ <b>Tayyor!</b>\n"
        f"Foydalanuvchi: {volunteer.fullname}\n" # Используем поле .fullname
        f"💰 <b>Yangi balans:</b> {volunteer.balance} ball"
    )
    return success_text, volunteer

# --- 3. ХЕНДЛЕРЫ ---

async def show_qr_handler(message: types.Message):
    await send_user_qr(message)

async def scan_qr_handler(message: types.Message):
    # В aiogram 2.x аргументы берем через get_args()
    args = message.get_args()
    if not args or not args.startswith('qr_'):
        return

    target_id = args.replace('qr_', '')
    
    # РАСПАКОВКА: получаем текст и объект волонтера
    result_text, volunteer = await process_qr_logic(message.from_user.id, target_id)
    
    # Отправляем ответ админу
    await message.answer(result_text, parse_mode="HTML")
    
    # Отправляем уведомление самому волонтеру
    if volunteer and "✅" in result_text:
        try:
            await message.bot.send_message(
                chat_id=volunteer.tg_id,
                text=(
                    f"🌟 <b>Tadbirda ishtirok etganingiz tasdiqlandi!</b>\n\n"
                    f"Sizga 10 ball berildi. Hozirgi balansingiz: <b>{volunteer.balance} ball</b>.\n"
                    f"Rahmat, tabiat himoyachisi! 🌿"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка отправки юзеру: {e}")

# --- 4. РЕГИСТРАЦИЯ ---
def register_qr_handlers(dp: Dispatcher):
    # Хендлер сканирования (обязательно ПЕРВЫМ)
    dp.register_message_handler(
        scan_qr_handler, 
        lambda m: m.get_args() and m.get_args().startswith('qr_'), 
        commands=["start"], 
        state="*"
    )
    # Кнопка показа QR
    dp.register_message_handler(
        show_qr_handler, 
        text="🌿 Mening QR-kodim", 
        state="*"
    )