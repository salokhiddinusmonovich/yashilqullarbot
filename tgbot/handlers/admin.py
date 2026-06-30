import asyncio
import logging
from aiogram import types, Dispatcher
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from app_telegram.models import TGUser
from django.db.models import Q
from aiogram.utils.exceptions import ChatNotFound, Unauthorized

logger = logging.getLogger(__name__)

async def run_broadcast(message: types.Message):
    # 1. Проверка прав через БД (самый надежный способ)
    user_in_db = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    
    # Если юзера нет в БД или у него нет флага is_admin — игнорим
    if not user_in_db or not getattr(user_in_db, 'is_admin', False):
        # Если хочешь, чтобы бот молчал для не-админов, оставь просто return
        # Если хочешь уведомление: await message.answer("❌ Sizda admin huquqi yo'q!")
        return

    # 2. Проверка на Reply
    if not message.reply_to_message:
        await message.answer("ℹ️ <b>Рассылка:</b>\nОтветь командой <code>/send</code> на пост (текст/фото), который нужно разослать всем волонтерам.", parse_mode="HTML")
        return

    # 3. Получаем ВСЕХ юзеров
    all_users = await sync_to_async(list)(TGUser.objects.all())
    
    if not all_users:
        await message.answer("❌ База пользователей пуста.")
        return

    await message.answer(f"🚀 <b>Рассылка запущена!</b>\nПолучателей: {len(all_users)}")

    count = 0
    blocked = 0
    errors = 0

    # 4. Цикл отправки с защитой от Flood
    for user in all_users:
        try:
            await message.reply_to_message.copy_to(chat_id=user.tg_id)
            count += 1
            # Задержка 0.05 сек — критически важна для больших баз (5000+ чел)
            await asyncio.sleep(0.05) 
        except exceptions.BotBlocked:
            blocked += 1
        except exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
            await message.reply_to_message.copy_to(chat_id=user.tg_id)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки на {user.tg_id}: {e}")
            errors += 1

    # 5. Итоговый отчет
    await message.answer(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📥 Получили: {count}\n"
        f"🚫 Блокировок: {blocked}\n"
        f"⚠️ Ошибок: {errors}",
        parse_mode="HTML"
    )

async def send_to_admins(message: types.Message):
    """
    Рассылка сообщений ТОЛЬКО администраторам проекта.
    Использование: Ответ (Reply) на сообщение + /adminsend
    """
    # 1. Проверка, что отправитель сам является админом
    user_in_db = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    if not user_in_db or not getattr(user_in_db, 'is_admin', False):
        return

    # 2. Проверка на Reply
    if not message.reply_to_message:
        await message.answer("⚠️ Ответь командой <code>/adminsend</code> на сообщение для админов!")
        return

    # 3. Фильтруем только админов
    admin_list = await sync_to_async(list)(TGUser.objects.filter(is_admin=True))
    
    await message.answer(f"⚡️ Отправляю сообщение команде админов ({len(admin_list)} чел.)...")

    count = 0
    for admin in admin_list:
        try:
            # Пересылаем сообщение
            await message.reply_to_message.copy_to(chat_id=admin.tg_id)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Не удалось отправить админу {admin.tg_id}: {e}")

    await message.answer(f"✅ Команда оповещена! Доставлено: {count} админам.")



async def target_broadcast(message: types.Message):
    """
    Рассылка конкретным людям по username или ФИО.
    Пример: /targetsend @shaxzod @admin_eco
    
    /targetsend @username — отправит одному.

    /targetsend @user1 @user2 @user3 — отправит нескольким.

    /targetsend Ivan_Ivanov — отправит по ФИО (если совпадет)
    """

    # 1. Проверка прав (как в прошлых функциях)
    user_in_db = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    if not user_in_db or not getattr(user_in_db, 'is_admin', False):
        return

    # 2. Проверка на Reply и наличие аргументов
    if not message.reply_to_message:
        await message.answer("⚠️ Ответь на сообщение и напиши юзернеймы через пробел!")
        return

    args = message.get_args().split()
    if not args:
        await message.answer("⚠️ Введи юзернеймы после команды. Пример:\n<code>/targetsend @nick1 @nick2</code>")
        return

    # 3. Чистим юзернеймы от значка @
    targets = [a.replace('@', '') for a in args]

    # 4. Ищем юзеров в базе (по username ИЛИ по fullname)
    query = Q(username__in=targets) | Q(fullname__in=targets)
    found_users = await sync_to_async(list)(TGUser.objects.filter(query))

    if not found_users:
        await message.answer("❌ Юзеры с такими никами не найдены в базе.")
        return

    await message.answer(f"🎯 Найдено {len(found_users)} чел. Начинаю отправку...")

    count = 0
    for user in found_users:
        try:
            await message.reply_to_message.copy_to(chat_id=user.tg_id)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Ошибка на {user.tg_id}: {e}")

    await message.answer(f"✅ Доставлено: {count} из {len(found_users)} выбранных.")


async def region_broadcast(message: types.Message):
    """
    Рассылка по конкретному региону.
    Пример: ответ на пост + /regionsend samarkand
    """
    # 1. Проверка прав (админ ли ты в БД)
    user_in_db = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    if not user_in_db or not getattr(user_in_db, 'is_admin', False):
        return

    # 2. Проверка на Reply
    if not message.reply_to_message:
        await message.answer("⚠️ Ответь на сообщение и напиши код региона!\nПример: <code>/regionsend tashkent_s</code>")
        return

    # 3. Получаем код региона из команды
    args = message.get_args().strip().lower()
    if not args:
        await message.answer("⚠️ Укажите код региона. Например: <code>tashkent_s, samarkand, bukhara</code>")
        return

    # 4. Ищем волонтеров только в этом регионе
    region_users = await sync_to_async(list)(TGUser.objects.filter(region=args))
    
    if not region_users:
        await message.answer(f"❌ В регионе <b>{args}</b> пока нет волонтеров.")
        return

    await message.answer(f"📍 Начинаю рассылку для <b>{len(region_users)}</b> волонтеров в регионе <b>{args}</b>...")

    count = 0
    for user in region_users:
        try:
            await message.reply_to_message.copy_to(chat_id=user.tg_id)
            count += 1
            await asyncio.sleep(0.05) # Защита от бана
        except Exception as e:
            logger.error(f"Ошибка отправки {user.tg_id}: {e}")

    await message.answer(f"✅ Готово! Регион <b>{args}</b> оповещен. Доставлено: {count}.")


async def check_user_subscription(message: types.Message):
    """
    Проверка: подписан ли конкретный юзер на канал.
    Использование: /check @username или /check 12345678 (ID)
    """
    # 1. Проверка прав (админ ли ты в БД)
    user_in_db = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    if not user_in_db or not getattr(user_in_db, 'is_admin', False):
        return

    # 2. Получаем аргументы (кого ищем)
    args = message.get_args().strip()
    if not args:
        await message.answer("⚠️ Введите юзернейм или ID после команды.\nПример: <code>/check @nickname</code>")
        return

    target_id = None
    args = message.get_args().strip()
    target_name = args.replace('@', '')

    # ПРОВЕРКА: Если ввели цифры, ищем по tg_id, если буквы — по username
    if target_name.isdigit():
        query = Q(tg_id=int(target_name))
    else:
        query = Q(username__iexact=target_name) | Q(fullname__icontains=target_name)

    user_query = await sync_to_async(TGUser.objects.filter(query).first)()

    if not user_query:
        await message.answer(f"❌ Юзер <b>{args}</b> не найден в базе.")
        return
    
    target_id = user_query.tg_id
    # Замени на ID своего канала (обязательно начинается с -100)
    CHANNEL_ID = -1002652020165

    try:
        # 4. Сама проверка через Telegram API
        member = await message.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=target_id)
        
        status_emoji = {
            'creator': '👑 Создатель',
            'administrator': '👨‍✈️ Админ',
            'member': '✅ Подписан',
            'left': '❌ Вышел из канала',
            'kicked': '🚫 Забанен'
        }
        
        res = status_emoji.get(member.status, f"Статус: {member.status}")
        
        await message.answer(
            f"👤 <b>Пользователь:</b> {user_query.fullname}\n"
            f"🆔 <b>ID:</b> <code>{target_id}</code>\n"
            f"📊 <b>Результат:</b> {res}",
            parse_mode="HTML"
        )

    except ChatNotFound:
        await message.answer("⚠️ Канал не найден. Проверь ID канала в коде.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка проверки: {e}")

async def remind_no_region(message: types.Message):
    """
    Рассылка-напоминание ВСЕМ пользователям, у которых не указан ПРАВИЛЬНЫЙ регион.
    (Пусто, NULL, или написано руками вместо нажатия кнопки).
    """
    # 1. Проверка прав
    user_in_db = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    if not user_in_db or not getattr(user_in_db, 'is_admin', False):
        return

    # 2. Ищем "неправильных" юзеров (Логика: берем всех, КРОМЕ тех, у кого правильный код)
    # ВНИМАНИЕ: Проверь, чтобы эти коды ТОЧНО совпадали с callback_data твоих кнопок!
    VALID_REGIONS = [
        'tashkent_s', 'tashkent_v', 'samarkand', 'bukhara', 'andijan', 
        'namangan', 'fergana', 'syrdarya', 'jizzakh', 'navoiy', 
        'kashkadarya', 'surkhandarya', 'khorezm', 'karakalpakstan'
    ]

    # exclude() убирает из списка тех, чье поле region есть в списке VALID_REGIONS.
    # В итоге остаются все, у кого пусто, null, или левый текст.
    users_without_region = await sync_to_async(list)(
        TGUser.objects.exclude(region__in=VALID_REGIONS)
    )

    if not users_without_region:
        await message.answer("✅ У всех пользователей в базе указан корректный регион! Рассылка не требуется.")
        return

    await message.answer(f"⚠️ Найдено <b>{len(users_without_region)}</b> пользователей без правильного региона. Формирую доклад...", parse_mode="HTML")

    # 3. ФОРМИРУЕМ ДОКЛАД (СПИСОК ЛЮДЕЙ)
    report_lines = []
    for i, u in enumerate(users_without_region, 1):
        name = u.fullname or "Без имени"
        uname = f"(@{u.username})" if u.username else ""
        # Показываем, что у них сейчас написано в поле region
        current_region = u.region if u.region else "Пусто"
        report_lines.append(f"{i}. {name} {uname} | ID: <code>{u.tg_id}</code> | В базе: <b>{current_region}</b>")
        
    report_text = "📋 <b>Список пользователей, которым уйдет рассылка:</b>\n\n" + "\n".join(report_lines)
    
    # Отправляем список (разбиваем на части, если людей много)
    for x in range(0, len(report_text), 4000):
        await message.answer(report_text[x:x+4000], parse_mode="HTML")

    await message.answer("🚀 Начинаю отправку сообщений... ⏳")

    # 4. Текст инструкции (немного поправил текст, чтобы они поняли, что надо именно нажать кнопку)
    text = (
        "👋 <b>Salom!</b>\n\n"
        "⚠️ Siz @YashilQollar botida hali o'z hududingizni to'g'ri tanlamagansiz "
        "(yoki tugmani bosish o'rniga matn yozib yuborgansiz).\n"
        "Loyihalarda ishtirok etish uchun hududni tugmalar orqali ko'rsatishingiz <b>shart</b>! ❗\n\n"
        "⚙️ <b>Nima qilish kerak:</b>\n"
        "Bot menyusidan <b>\"👤 Mening profilim\"</b> ➡️ <b>\"📍 Hududni o'zgartirish\"</b> "
        "tugmasini bosing va yashash joyingizni faqat <b>tugmalar orqali</b> tanlang. 🌿"
    )

    count = 0
    blocked = 0
    errors = 0

    # 5. Отправка сообщений
    for user in users_without_region:
        if not user.tg_id:
            continue
        try:
            await message.bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")
            count += 1
            await asyncio.sleep(0.05)  
        except exceptions.BotBlocked:
            blocked += 1
        except exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
            await message.bot.send_message(chat_id=user.tg_id, text=text, parse_mode="HTML")
            count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки {user.tg_id}: {e}")
            errors += 1

    # 6. Итоговый отчет
    await message.answer(
        f"✅ <b>Напоминание завершено!</b>\n\n"
        f"🎯 Людей с ошибкой в регионе: {len(users_without_region)}\n"
        f"📥 Успешно отправлено: {count}\n"
        f"🚫 Заблокировали бота: {blocked}\n"
        f"⚠️ Прочих ошибок: {errors}",
        parse_mode="HTML"
    )

def register_admin(dp: Dispatcher):
    dp.register_message_handler(run_broadcast, commands=['send'], state="*")
    dp.register_message_handler(send_to_admins, commands=['adminsend'], state="*") # <-- Новая строка
    dp.register_message_handler(target_broadcast, commands=['targetsend'], state="*")
    dp.register_message_handler(region_broadcast, commands=['regionsend'], state="*")
    dp.register_message_handler(check_user_subscription, commands=['check'], state="*")
    dp.register_message_handler(remind_no_region, commands=['remindregion'], state="*")