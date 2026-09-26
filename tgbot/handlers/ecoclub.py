from html import escape

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from django.utils import timezone

from app_telegram.models import TGUser, EcoProject, ProjectParticipation
from tgbot.i18n import t, variants
from tgbot.services.photo_cache import send_cached_photo, file_cache_key

CHANNEL_ID = "@yashilqollar"
TASHKENT = ['tashkent_s', 'tashkent_v']
PAST_LIMIT = 10


class EventStates(StatesGroup):
    # Старый сценарий (reply-кнопка "Ro'yxatdan o'tish" под последним
    # показанным мероприятием). Оставлен только чтобы кнопки из старых
    # сообщений не ломались — новые списки используют inline-кнопку
    # под КАЖДЫМ мероприятием (evreg:<id>).
    waiting_for_registration = State()


# --- КЛАВИАТУРЫ ---

def get_events_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(t("btn_upcoming")), KeyboardButton(t("btn_past")))
    kb.row(KeyboardButton(t("btn_back")))
    return kb


def channel_kb():
    return InlineKeyboardMarkup().add(
        InlineKeyboardButton(t("btn_join_channel"), url=f"https://t.me/{CHANNEL_ID.replace('@', '')}")
    )


async def _is_subscribed(bot, tg_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=tg_id)
        return member.status in ('creator', 'administrator', 'member')
    except Exception as e:
        print(f"Subscription check error: {e}")
        return True  # не блокируем запись, если Telegram не ответил


def _event_header(p) -> str:
    date = timezone.localtime(p.date).strftime('%d.%m.%Y %H:%M')
    text = f"🚀 <b>{escape(p.title)}</b>\n🗓 {date}"
    if p.location_name:
        text += f" · 📍 {escape(p.location_name)}"
    text += "\n\n"
    if p.description:
        text += f"{escape(p.description)}\n\n"
    return text


# --- ХЕНДЛЕРЫ ---

async def show_events_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(t("events_title"), reply_markup=get_events_menu())


async def list_upcoming_events(message: types.Message, state: FSMContext):
    await state.finish()

    user = await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id).first)()
    if not user:
        await message.answer(t("not_registered"))
        return
    if user.region not in TGUser.Region.values:
        await message.answer(t("events_no_region"), reply_markup=get_events_menu())
        return

    regions = TASHKENT if user.region in TASHKENT else [user.region]
    # participants_count одним annotate() — без отдельного count() на каждое мероприятие
    projects = await sync_to_async(list)(
        EcoProject.objects.filter(is_active=True, date__gt=timezone.now(), region__in=regions)
        .annotate(participants_count=Count('participants', filter=~Q(participants__status='rejected')))
        .order_by('date')
    )

    if not projects:
        await message.answer(t("events_none"), reply_markup=get_events_menu())
        return

    # один запрос — на какие из этих мероприятий юзер уже записан
    joined = await sync_to_async(set)(
        ProjectParticipation.objects.filter(user=user, project__in=projects).values_list('project_id', flat=True)
    )

    for p in projects:
        text = _event_header(p) + t("event_seats", count=p.participants_count, max=p.max_participants) + "\n"

        kb = None
        if p.id in joined:
            text += "\n" + t("event_already")
        elif p.participants_count >= p.max_participants:
            text += "\n" + t("event_full")
        else:
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton(t("btn_event_register"), callback_data=f"evreg:{p.id}")
            )

        if p.photo:
            try:
                # Одна и та же фотка шлётся всем юзерам региона — кэш file_id
                # экономит повторную загрузку с диска и аплоад в Telegram.
                await send_cached_photo(
                    message, file_cache_key(p.photo.path), lambda path=p.photo.path: open(path, 'rb'),
                    caption=text if len(text) <= 1024 else None, reply_markup=kb,
                )
                if len(text) > 1024:
                    await message.answer(text, reply_markup=kb)
                continue
            except Exception:
                pass
        await message.answer(text, reply_markup=kb)


_JOIN_TEXT = {"gone": "event_gone", "already": "event_already_applied", "full": "event_no_seats", "region": "event_other_region"}


@sync_to_async
def _register(tg_id: int, project_id: int):
    """Возвращает (ключ_ответа, project). Логика общая с Mini App — app_telegram/services.py."""
    from app_telegram.services import join_event
    user = TGUser.objects.filter(tg_id=tg_id).first()
    if not user:
        return "not_registered", None
    code, project = join_event(user, project_id)
    return ("ok" if code == "ok" else _JOIN_TEXT[code]), project


async def _do_register(message: types.Message, tg_id: int, project_id: int, bot):
    # Сначала быстрые проверки в БД, и только потом — сетевой запрос
    # в Telegram на проверку подписки.
    already = await sync_to_async(
        ProjectParticipation.objects.filter(user__tg_id=tg_id, project_id=project_id).exists
    )()
    if already:
        await message.answer(t("event_already_applied"), reply_markup=get_events_menu())
        return

    if not await _is_subscribed(bot, tg_id):
        await message.answer(t("event_subscribe_first"), reply_markup=channel_kb())
        return

    result, project = await _register(tg_id, project_id)
    if result != "ok":
        await message.answer(t(result), reply_markup=get_events_menu())
        return

    # Регистрация сразу approved — ссылку на группу даём тут же.
    text = t("event_accepted", title=escape(project.title))
    if project.chat_link:
        text += t("event_accepted_chat", link=project.chat_link)
    from .miniapp import open_app_kb
    app_kb = open_app_kb(bot, "btn_open_event_app", event=project.id)
    await message.answer(text, reply_markup=app_kb or get_events_menu(), disable_web_page_preview=True)


async def register_callback(call: types.CallbackQuery):
    await call.answer()
    project_id = int(call.data.split(":", 1)[1])
    await _do_register(call.message, call.from_user.id, project_id, call.bot)


async def process_registration(message: types.Message, state: FSMContext):
    """Старая reply-кнопка из сообщений, отправленных до обновления."""
    project_id = (await state.get_data()).get('project_id')
    await state.finish()
    if not project_id:
        await message.answer(t("error_retry"), reply_markup=get_events_menu())
        return
    await _do_register(message, message.from_user.id, project_id, message.bot)


async def list_past_events(message: types.Message, state: FSMContext):
    await state.finish()
    past_events = await sync_to_async(lambda: list(
        EcoProject.objects.filter(date__lt=timezone.now()).order_by('-date')[:PAST_LIMIT]
    ))()

    if not past_events:
        await message.answer(t("past_empty"))
        return

    for event in past_events:
        caption = _event_header(event).strip()
        if event.photo:
            try:
                await send_cached_photo(
                    message, file_cache_key(event.photo.path), lambda path=event.photo.path: open(path, 'rb'),
                    caption=caption[:1024],
                )
                continue
            except Exception as e:
                print(f"Photo error: {e}")
        await message.answer(caption)


# --- РЕГИСТРАЦИЯ ---

def register_eco_clubs(dp: Dispatcher):
    dp.register_message_handler(show_events_menu, text=variants("btn_events"), state="*")
    dp.register_message_handler(list_upcoming_events, text=variants("btn_upcoming"), state="*")
    dp.register_message_handler(list_past_events, text=variants("btn_past"), state="*")
    dp.register_callback_query_handler(register_callback, lambda c: c.data.startswith("evreg:"), state="*")
    dp.register_message_handler(
        process_registration,
        text=variants("btn_event_register"),
        state=EventStates.waiting_for_registration,
    )
