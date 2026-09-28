import asyncio
import django
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.redis import RedisStorage2

# --- 1. ИНИЦИАЛИЗАЦИЯ DJANGO (ДО ИМПОРТА ХЕНДЛЕРОВ) ---
def setup_django():
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "dj_ac.settings"
    )
    os.environ.update({'DJANGO_ALLOW_ASYNC_UNSAFE': "true"})
    django.setup()

setup_django()

# --- 2. ТЕПЕРЬ ИМПОРТЫ ХЕНДЛЕРОВ (ОНИ ТЕПЕРЬ НЕ УПАДУТ) ---
from tgbot.config import load_config
from tgbot.filters.admin import AdminFilter
from tgbot.handlers.admin import register_admin
from tgbot.handlers.start import register_user
from tgbot.handlers.profile import register_profile, register_back
from tgbot.handlers.register import register_register
from tgbot.handlers.about import register_about_and_team
from tgbot.handlers.ecoclub import register_eco_clubs
from tgbot.handlers.shop import register_shop
from tgbot.handlers.qr_handler import register_qr_handlers
from tgbot.handlers.feedback import register_feedback
from tgbot.handlers.contact_with_team import register_project_handlers
from tgbot.handlers.link_account import register_link_account_handlers
from tgbot.handlers.admin_panel import register_admin_panel
from tgbot.handlers.help import register_help
from tgbot.handlers.assistant import register_assistant, register_free_questions
from tgbot.handlers.invite import register_invite
from tgbot.handlers.reminders import register_reminders
from tgbot.services.reminders import reminders_loop
from tgbot.services.cert_delivery import certificates_loop
from tgbot.handlers.certs import register_certs
from tgbot.handlers.impact import register_impact
from tgbot.handlers.wrapped import register_wrapped
from tgbot.handlers.spots import register_spots, register_spots_start
from tgbot.handlers.admin_scan import register_admin_scan
from tgbot.services.impact_prompt import impact_prompt_loop
from tgbot.services.wrapped import wrapped_loop
from tgbot.handlers.digest import register_digest
from tgbot.services.digest import digest_loop
from tgbot.handlers.language import register_language
from tgbot.handlers.miniapp import register_miniapp, setup_menu_button
from tgbot.middlewares.environment import EnvironmentMiddleware
from tgbot.middlewares.activity import ActivityMiddleware
from tgbot.middlewares.i18n import I18nMiddleware
from tgbot.services.daily_report import daily_report_loop

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
#  ГЛАВНЫЙ ПЕРЕКЛЮЧАТЕЛЬ РЕЖИМА
#
#  True  → Shop / QR-код / Eco-events(проекты) / Регистрация ИДУТ
#          ЧЕРЕЗ MINI APP, соответствующие текстовые кнопки бота
#          ВЫКЛЮЧЕНЫ (не регистрируются вообще).
#
#  False → всё как было ИЗНАЧАЛЬНО, до Mini App: все текстовые кнопки
#          работают, обычная регистрация через бота как раньше.
#
#  Чтобы вернуть всё "как было" в будущем — меняешь ТОЛЬКО эту строку,
#  ничего больше трогать не нужно.
# ═══════════════════════════════════════════════════════════════════
USE_MINI_APP = False


# --- 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def register_all_middlewares(dp, config):
    dp.setup_middleware(EnvironmentMiddleware(config=config))
    dp.setup_middleware(ActivityMiddleware())
    dp.setup_middleware(I18nMiddleware())      # язык юзера → t("...") в хендлерах


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    # ── Работает ВСЕГДА, независимо от режима ──
    register_admin(dp)               # админ-панель — не относится к Mini App вообще
    register_spots_start(dp)         # t.me/<бот>?start=spot — «📍 Iflos joy» из Mini App (раньше общего /start)
    register_user(dp)                # /start — точка входа
    # Язык и инструкция — ДО хендлеров состояний: кнопки «🌐» и «❓»
    # должны срабатывать даже посреди регистрации, а не сохраняться как ответ.
    register_language(dp)
    register_miniapp(dp)             # /app — открыть Mini App
    register_help(dp)                # ❓ Qo'llanma / /help
    register_invite(dp)              # 👥 пригласи друга / /invite
    register_reminders(dp)           # кнопки в напоминаниях о мероприятиях
    register_certs(dp)               # 🎓 /sertifikat
    register_impact(dp)              # 📊 /natija — координатор вносит итоги мероприятия (кг, деревья, фото)
    register_wrapped(dp)             # 🎁 /yakun — итоги года
    register_spots(dp)               # 📍 Iflos joy — сообщить о мусорном месте (кнопка меню, /iflos)
    register_admin_scan(dp)          # 👑 is_admin: отметить на любом мероприятии (скриншот QR, /belgila)
    register_digest(dp)              # 📅 недельный дайджест: /digest, «🔕»
    register_register(dp)            # регистрация — СТАТИКА, всегда через бота,
                                      # не переключается флагом USE_MINI_APP
    register_about_and_team(dp)      # статичная инфа "о нас"/команда — не дублируется в Mini App
    register_eco_clubs(dp)           # инфо про эко-клубы — не дублируется в Mini App
    register_feedback(dp)            # рейтинг после посещения (пуш от бота, не кнопка меню)
    register_link_account_handlers(dp)
    if USE_MINI_APP:
        # ── РЕЖИМ MINI APP ──
        # Ничего из старых текстовых кнопок ниже НЕ регистрируется —
        # вместо них юзер открывает Mini App через кнопку меню бота.
        # Регистрация сюда НЕ входит — она всегда работает (см. выше).
        #
        # register_profile(dp)           # ← профиль теперь через Mini App
        # register_project_handlers(dp)  # ← эко-события/проекты теперь через Mini App
        # register_shop(dp)              # ← магазин теперь через Mini App
        # register_qr_handlers(dp)       # ← QR-код теперь через Mini App
        pass
    else:
        # ── СТАРЫЙ ТЕКСТОВЫЙ РЕЖИМ (как было до Mini App) ──
        register_profile(dp)
        register_project_handlers(dp)
        register_shop(dp)
        register_qr_handlers(dp)

    # 🤖 Помощник (FAQ + бесплатный ИИ) и 🎙 команды админа — свои состояния,
    # кнопки меню с state="*" выше по-прежнему срабатывают первыми.
    register_assistant(dp)

    # «⬅️ Назад» → главное меню. После профиля: там «Назад» из выбора
    # региона ведёт в меню профиля, а не в главное.
    register_back(dp)

    # Админка в боте (/admin) — регистрируется ПОСЛЕДНЕЙ: её хендлеры
    # состояний ("введите @username") ловят любой текст, и так /start и
    # кнопки меню продолжают работать, даже если админ бросил ввод на полпути.
    register_admin_panel(dp)

    # 🤖 Любой текст/голосовое, которое никто не обработал, — вопрос помощнику (не молчим).
    register_free_questions(dp)

    print(f"Handlers registered! (mode: {'MINI APP' if USE_MINI_APP else 'TEXT'})")


# --- 4. ОСНОВНАЯ ЛОГИКА ЗАПУСКА ---
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    logger.info("Starting bot")

    config = load_config(".env")

    # Настройка хранилища (Redis или Memory)
    if config.redis.use_redis:
        storage = RedisStorage2(
            host=config.redis.host,
            port=config.redis.port,
            db=5,
            pool_size=10,
            prefix='bot_fsm'
        )
    else:
        storage = MemoryStorage()

    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dp = Dispatcher(bot, storage=storage)

    bot['config'] = config

    # Регистрация всего
    register_all_middlewares(dp, config)
    register_all_filters(dp)
    register_all_handlers(dp)

    # Кнопка Mini App рядом с полем ввода (если задан MINIAPP_URL)
    await setup_menu_button(bot)

    # Ежедневный отчёт админам (21:00 по Ташкенту, см. DAILY_REPORT_HOUR)
    asyncio.create_task(daily_report_loop(bot))
    # Напоминания о мероприятиях: накануне в 19:00 и за 2 часа (tgbot/services/reminders.py)
    asyncio.create_task(reminders_loop(bot))
    # 🎓 Сертификаты — наутро после мероприятия всем, кто пришёл (tgbot/services/cert_delivery.py)
    asyncio.create_task(certificates_loop(bot))
    # 📅 Дайджест мероприятий на неделю — по понедельникам в 10:00 (tgbot/services/digest.py)
    asyncio.create_task(digest_loop(bot))
    # 📊 «Введите итоги» координаторам через 3 ч после начала мероприятия (tgbot/services/impact_prompt.py)
    asyncio.create_task(impact_prompt_loop(bot))
    # 🎁 Итоги года — 20 декабря всем, кто был на мероприятиях (tgbot/services/wrapped.py)
    asyncio.create_task(wrapped_loop(bot))

    # Запуск polling
    try:
        await dp.start_polling(
            allowed_updates=[
                "message",
                "edited_message",
                "callback_query",
                "my_chat_member",
                "chat_member",
            ]
        )
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        session = await bot.get_session()
        await session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")