import qrcode
from io import BytesIO
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async
from django.utils import timezone

# ВНИМАНИЕ: Проверь, чтобы путь к моделям был правильным (app_telegram — это имя твоего приложения)
from app_telegram.models import TGUser, ProjectParticipation, EcoProject 

# ТВОЙ СПИСОК АДМИНОВ (ID)
ADMIN_IDS = [7336334074, 998920105472, 998998951002, 998904815816, 998908291932]

# --- 1. ГЕНЕРАЦИЯ QR-КОДА ---
async def send_user_qr(message: types.Message):
    """Генерирует QR со ссылкой t.me/bot?start=qr_ID"""
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

# --- 2. ЛОГИКА ПРОВЕРКИ И НАЧИСЛЕНИЯ (DATABASE) ---
@sync_to_async
def process_qr_logic(admin_id, target_tg_id):
    """Стыковка админа, волонтера и проекта в БД"""
    # Проверка на админа
    if admin_id not in ADMIN_IDS:
        return "❌ Sizda adminlik huquqi yo'q!", None

    # Поиск волонтера
    volunteer = TGUser.objects.filter(tg_id=target_tg_id).first()
    if not volunteer:
        return "❌ Foydalanuvchi topilmadi!", None

    # Умный поиск региона (Ташкент город + область)
    search_regions = [volunteer.region]
    if volunteer.region in ['tashkent_s', 'tashkent_v']:
        search_regions = ['tashkent_s', 'tashkent_v']

    today = timezone.now().date()
    
    # Ищем проект (сначала строго по дате, потом любой активный в регионе)
    project = EcoProject.objects.filter(
        is_active=True, 
        date__date=today, 
        region__in=search_regions
    ).first()

    if not project:
        project = EcoProject.objects.filter(
            is_active=True, 
            region__in=search_regions
        ).first()

    if not project:
        return f"❌ {volunteer.get_region_display()}da faol loyiha topilmadi!", None

    # Проверка регистрации на проект
    participation = ProjectParticipation.objects.filter(project=project, user=volunteer).first()
    if not participation:
        return f"❌ Волонтер '{project.title}' лойиҳасига рўйхатдан ўтмаган!", None

    if participation.status == 'attended':
        return f"⚠️ {volunteer.fullname} аллақачон тасдиқланган!", None

    # СОХРАНЕНИЕ (Твоя модель сама добавит +10 баллов в методе save)
    participation.status = 'attended'
    participation.save()
    
    # Обновляем данные объекта volunteer из базы, чтобы увидеть новый баланс
    volunteer.refresh_from_db()
    
    success_msg = (
        f"✅ <b>Tayyor!</b>\n{volunteer.fullname} kelgani tasdiqlandi.\n"
        f"💰 <b>Balans:</b> {volunteer.balance} ball"
    )
    return success_msg, volunteer

# --- 3. ХЕНДЛЕРЫ ДЛЯ ДИСПЕТЧЕРА ---

async def show_qr_handler(message: types.Message):
    """По кнопке 'Mening QR-kodim'"""
    await send_user_qr(message)

async def scan_qr_handler(message: types.Message, command: types.Command):
    """Когда админ сканирует QR (start с аргументом qr_...)"""
    target_id = command.args.replace('qr_', '')
    
    # Запускаем логику
    result_text, volunteer = await process_qr_logic(message.from_user.id, target_id)
    
    # Ответ админу
    await message.answer(result_text, parse_mode="HTML")
    
    # ОТПРАВКА СООБЩЕНИЯ САМОМУ ВОЛОНТЕРУ (Тот самый пункт про "30 баллов")
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
            print(f"Не удалось отправить сообщение юзеру {volunteer.tg_id}: {e}")

# --- 4. РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ---
def register_qr_handlers(dp: Dispatcher):
    # Хендлер сканера (срабатывает на /start qr_...)
    dp.register_message_handler(
        scan_qr_handler, 
        lambda m: m.get_args() and m.get_args().startswith('qr_'), 
        commands=["start"], 
        state="*"
    )
    # Хендлер кнопки в меню
    dp.register_message_handler(
        show_qr_handler, 
        text="🌿 Mening QR-kodim", 
        state="*"
    )