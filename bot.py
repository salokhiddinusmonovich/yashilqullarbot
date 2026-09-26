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
from tgbot.handlers.language import register_language
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
    register_user(dp)                # /start — точка входа
    # Язык и инструкция — ДО хендлеров состояний: кнопки «🌐» и «❓»
    # должны срабатывать даже посреди регистрации, а не сохраняться как ответ.
    register_language(dp)
    register_help(dp)                # ❓ Qo'llanma / /help
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

    # «⬅️ Назад» → главное меню. После профиля: там «Назад» из выбора
    # региона ведёт в меню профиля, а не в главное.
    register_back(dp)

    # Админка в боте (/admin) — регистрируется ПОСЛЕДНЕЙ: её хендлеры
    # состояний ("введите @username") ловят любой текст, и так /start и
    # кнопки меню продолжают работать, даже если админ бросил ввод на полпути.
    register_admin_panel(dp)

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

    # Ежедневный отчёт админам (21:00 по Ташкенту, см. DAILY_REPORT_HOUR)
    asyncio.create_task(daily_report_loop(bot))

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