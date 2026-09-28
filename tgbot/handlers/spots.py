"""
📍 Iflos joy — волонтёр сообщает о замусоренном месте (кнопка меню, /iflos, t.me/<бот>?start=spot).

Шаги: 📸 1–5 фото → 📍 геолокация (своя или точка на карте) → регион (сам по OpenStreetMap) →
🗑 сколько → ♻️ какой → 🚶 можно ли подойти → ✍️ комментарий → ✅ отправить.
Рядом (100 м) уже есть открытое сообщение — предлагаем просто подтвердить его.
Только админам (галочка is_admin, роль не важна) — фото, точка и карточка с кнопками;
автору — каждый шаг: принято (+5), мероприятие назначено, убрано (+10, «до / после»), отклонено.
Логика и хранение — app_telegram/spots.py.
"""
import asyncio
import logging
from datetime import datetime, timezone as dt_tz
from html import escape
from io import BytesIO

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, InputFile, InputMediaPhoto, KeyboardButton,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo)
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from django.utils import timezone

from tgbot.i18n import t, variants, region_label, current_lang, REGIONS
from tgbot.services.lang import _aclient, lang_of, langs_of

log = logging.getLogger(__name__)


class SpotStates(StatesGroup):
    photos = State()
    location = State()
    details = State()      # регион / размер / вид / доступ — кнопками
    note = State()
    confirm = State()


def _draft(tg: int) -> str:
    return f"spot:draft:{tg}"


def _cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup().add(InlineKeyboardButton(t("spot_btn_cancel"), callback_data="spx"))


@sync_to_async
def _user(tg: int):
    from app_telegram.models import TGUser
    return TGUser.objects.filter(tg_id=tg).first()


async def _menu(tg: int):
    from tgbot.keyboards.reply import main_menu
    return await main_menu(tg)


# ─────────── волонтёр ───────────

async def spot_start(message: types.Message, state: FSMContext):
    from app_telegram import spots as SP
    user = await _user(message.from_user.id)
    if not user:
        await message.answer(t("spot_register"))
        return
    if not await sync_to_async(SP.can_report)(message.from_user.id):
        await message.answer(t("spot_limit", n=SP.PER_DAY))
        return
    await state.finish()
    await _aclient().delete(_draft(message.from_user.id))
    await SpotStates.photos.set()
    await message.answer(t("spot_intro"), reply_markup=ReplyKeyboardRemove())
    await message.answer(t("spot_q_photos"), reply_markup=_cancel_kb())


async def photo_input(message: types.Message, state: FSMContext):
    from app_telegram.spots import MAX_PHOTOS
    if message.photo:
        fid = message.photo[-1].file_id
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        fid = message.document.file_id
    else:
        return
    r = _aclient()
    key = _draft(message.from_user.id)
    n = await r.rpush(key, fid)            # список в Redis — альбом приходит пачкой, без гонок
    await r.expire(key, 86400)
    if n > MAX_PHOTOS:
        await r.ltrim(key, 0, MAX_PHOTOS - 1)
        if n == MAX_PHOTOS + 1:
            await message.answer(t("spot_photo_max", n=MAX_PHOTOS))
        return
    mg = message.media_group_id
    if mg and not await r.set(f"spot:mg:{mg}", 1, nx=True, ex=120):
        return                              # на альбом отвечаем один раз
    kb = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton(t("spot_btn_next"), callback_data="spn"),
                                               InlineKeyboardButton(t("spot_btn_cancel"), callback_data="spx"))
    await message.answer(t("spot_photo_ok"), reply_markup=kb)


async def photos_text(message: types.Message):
    await message.answer(t("spot_q_photos"), reply_markup=_cancel_kb())


def _location_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton(t("spot_btn_here"), request_location=True))
    kb.add(KeyboardButton(t("spot_btn_cancel")))
    return kb


async def next_callback(call: types.CallbackQuery, state: FSMContext):
    if await state.get_state() != SpotStates.photos.state:
        await call.answer()
        return
    if not await _aclient().llen(_draft(call.from_user.id)):
        await call.answer(t("spot_need_photo"), show_alert=True)
        return
    await call.answer()
    await SpotStates.location.set()
    await call.message.answer(t("spot_q_location"), reply_markup=_location_kb())


async def location_input(message: types.Message, state: FSMContext):
    from app_telegram import spots as SP
    from tgbot.services import geo
    loc = message.location or (message.venue.location if message.venue else None)
    lat, lon = loc.latitude, loc.longitude
    g = await geo.reverse(lat, lon, current_lang.get())
    if (g and g["country"] and g["country"] != "uz") or (not g and not SP.in_uz_box(lat, lon)):
        await message.answer(t("spot_not_uz"), reply_markup=_location_kb())
        return
    region = (g or {}).get("region")
    await state.update_data(lat=lat, lon=lon, region=region, guess=region or SP.nearest_region(lat, lon),
                            address=(g or {}).get("address", ""))
    await SpotStates.details.set()
    await message.answer(t("spot_loc_ok"), reply_markup=ReplyKeyboardRemove())
    near = await sync_to_async(SP.near_open)(lat, lon)
    if near:
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton(t("spot_btn_same"), callback_data=f"spd:{near['id']}"),
            InlineKeyboardButton(t("spot_btn_other"), callback_data="spnew"))
        await message.answer(t("spot_dup_q", id=near["id"], status=t(f"spot_st_{near['status']}")), reply_markup=kb)
        return
    await _after_location(message, state)


async def location_text(message: types.Message, state: FSMContext):
    if (message.text or "").strip() in variants("spot_btn_cancel"):
        await _cancel(message, state)
        return
    await message.answer(t("spot_q_location"), reply_markup=_location_kb())


def _regions_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(*[InlineKeyboardButton(region_label(code), callback_data=f"spr:{code}") for code in REGIONS])
    return kb


async def _after_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("region"):
        await _ask_size(message)
        return
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(t("spot_btn_region_ok", region=region_label(data["guess"])), callback_data=f"spr:{data['guess']}"),
        InlineKeyboardButton(t("spot_btn_region_other"), callback_data="spro"))
    await message.answer(t("spot_q_region"), reply_markup=kb)


async def _ask_size(message: types.Message):
    from app_telegram.spots import SIZES
    kb = InlineKeyboardMarkup(row_width=1).add(*[InlineKeyboardButton(t(f"spot_size_{s}"), callback_data=f"sps:{s}") for s in SIZES])
    await message.answer(t("spot_q_size"), reply_markup=kb)


async def details_callback(call: types.CallbackQuery, state: FSMContext):
    """Кнопки шагов: spd (это то же место) / spnew / spr:<регион> / spro / sps / spk / spa."""
    from app_telegram import spots as SP
    if await state.get_state() != SpotStates.details.state:
        await call.answer()
        return
    await call.answer()
    key, _, val = call.data.partition(":")
    msg = call.message
    try:
        await msg.edit_reply_markup(None)
    except exceptions.TelegramAPIError:
        pass
    if key == "spd":
        n = await sync_to_async(SP.confirm)(int(val), call.from_user.id)
        await state.finish()
        await _aclient().delete(_draft(call.from_user.id))
        await msg.answer(t("spot_dup_done", id=val, n=n), reply_markup=await _menu(call.from_user.id))
    elif key == "spnew":
        await _after_location(msg, state)
    elif key == "spro":
        await msg.answer(t("spot_q_region"), reply_markup=_regions_kb())
    elif key == "spr" and val in REGIONS:
        await state.update_data(region=val)
        await _ask_size(msg)
    elif key == "sps" and val in SP.SIZES:
        await state.update_data(size=val)
        kb = InlineKeyboardMarkup(row_width=2).add(*[InlineKeyboardButton(t(f"spot_kind_{k}"), callback_data=f"spk:{k}") for k in SP.KINDS])
        await msg.answer(t("spot_q_kind"), reply_markup=kb)
    elif key == "spk" and val in SP.KINDS:
        await state.update_data(kind=val)
        kb = InlineKeyboardMarkup(row_width=1).add(*[InlineKeyboardButton(t(f"spot_acc_{a}"), callback_data=f"spa:{a}") for a in SP.ACCESS])
        await msg.answer(t("spot_q_access"), reply_markup=kb)
    elif key == "spa" and val in SP.ACCESS:
        await state.update_data(access=val)
        await SpotStates.note.set()
        kb = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton(t("spot_btn_skip"), callback_data="spskip"),
                                                   InlineKeyboardButton(t("spot_btn_cancel"), callback_data="spx"))
        await msg.answer(t("spot_q_note"), reply_markup=kb)


async def note_input(message: types.Message, state: FSMContext):
    await state.update_data(note=(message.text or "")[:500])
    await _show_confirm(message, state)


async def skip_note(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if await state.get_state() == SpotStates.note.state:
        await _show_confirm(call.message, state)


async def _show_confirm(message: types.Message, state: FSMContext):
    data = await state.get_data()
    n = await _aclient().llen(_draft(message.chat.id))
    await SpotStates.confirm.set()
    kb = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton(t("spot_btn_send"), callback_data="spok"),
                                               InlineKeyboardButton(t("spot_btn_cancel"), callback_data="spx"))
    await message.answer(t("spot_confirm", n=n, region=region_label(data["region"]), address=escape(data.get("address") or "—"),
                           size=t(f"spot_size_{data['size']}"), kind=t(f"spot_kind_{data['kind']}"),
                           access=t(f"spot_acc_{data['access']}"), note=escape(data.get("note") or "—")), reply_markup=kb)


async def send_callback(call: types.CallbackQuery, state: FSMContext):
    from app_telegram import spots as SP
    if await state.get_state() != SpotStates.confirm.state:
        await call.answer()
        return
    await call.answer(t("spot_sending"))
    tg = call.from_user.id
    data = await state.get_data()
    r = _aclient()
    fids = await r.lrange(_draft(tg), 0, -1)
    photos = []
    for fid in fids:
        buf = BytesIO()
        try:
            await call.bot.download_file_by_id(fid, destination=buf)
            photos.append(buf.getvalue())
        except Exception:
            log.exception("spot photo download")
    user = await _user(tg)
    if not user or not photos:
        await call.message.answer(t("spot_need_photo"))
        return
    spot = await sync_to_async(SP.create)(user, data["lat"], data["lon"], data["region"], data["size"], data["kind"],
                                           data["access"], data.get("note", ""), data.get("address", ""), photos)
    await state.finish()
    await r.delete(_draft(tg))
    try:
        await call.message.edit_reply_markup(None)
    except exceptions.TelegramAPIError:
        pass
    await call.message.answer(t("spot_sent", id=spot["id"]), reply_markup=await _menu(tg))
    asyncio.create_task(notify_moderators(call.bot, spot, fids, user))


async def _cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await _aclient().delete(_draft(message.chat.id))
    await message.answer(t("spot_cancelled"), reply_markup=await _menu(message.chat.id))


async def cancel_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    try:
        await call.message.edit_reply_markup(None)
    except exceptions.TelegramAPIError:
        pass
    await _cancel(call.message, state)


# ─────────── модераторы ───────────

def card_text(s: dict, lang: str, name: str = "", username: str = "") -> str:
    from app_telegram.spots import maps_links
    links = maps_links(s["lat"], s["lon"])
    who = f'<a href="tg://user?id={s["tg"]}">{escape(name or s.get("name") or "—")}</a>' + (f" @{escape(username)}" if username else "")
    return t("spot_card", lang, id=s["id"], who=who, region=region_label(s["region"], lang) if s.get("region") else "—",
             address=escape(s.get("address") or "—"), size=t(f"spot_size_{s['size']}", lang), kind=t(f"spot_kind_{s['kind']}", lang),
             access=t(f"spot_acc_{s['access']}", lang), note=escape(s.get("note") or "—"), confirms=s.get("confirms", 0),
             date=timezone.localtime(datetime.fromtimestamp(s["created"], tz=dt_tz.utc)).strftime("%d.%m.%Y %H:%M"),
             google=links["google"], yandex=links["yandex"], status=t(f"spot_st_{s['status']}", lang))


def mod_kb(s: dict, lang: str) -> InlineKeyboardMarkup | None:
    b = lambda key, act: InlineKeyboardButton(t(key, lang), callback_data=f"sm:{act}:{s['id']}")
    st = s["status"]
    kb = InlineKeyboardMarkup(row_width=2)
    if st == "new":
        kb.add(b("spot_m_accept", "a"), b("spot_m_reject", "r"))
        kb.add(b("spot_m_event", "e"), b("spot_m_dup", "d"))
    elif st == "accepted":
        kb.add(b("spot_m_event", "e"), b("spot_m_clean", "c"))
    elif st == "planned":
        kb.add(b("spot_m_clean", "c"))
    else:
        return None
    return kb


def _file(rel: str) -> InputFile:
    """Фото из MEDIA_ROOT — отправляем файлом (не ссылкой: Telegram не нужно ходить к нам на сервер)."""
    from django.conf import settings
    from pathlib import Path
    return InputFile(str(Path(settings.MEDIA_ROOT) / rel))


async def notify_moderators(bot, spot: dict, fids: list | None, author) -> int:
    """Карточка модераторам. fids — file_id из чата с ботом; None — фото с диска (сообщение из Mini App).
    После первой отправки берём file_id из ответа Telegram, чтобы остальным не загружать файлы заново."""
    from app_telegram import spots as SP
    mods = await sync_to_async(SP.moderators_for)(spot["region"])
    langs = await langs_of([m.tg_id for m in mods])
    items = list(fids) if fids else [_file(p) for p in spot["photos"]]
    sent = 0
    for m in mods:
        lang = langs.get(m.tg_id) or "uz"
        try:
            if len(items) > 1:
                res = await bot.send_media_group(m.tg_id, [InputMediaPhoto(f) for f in items])
                if res and getattr(res[0], "photo", None):
                    items = [x.photo[-1].file_id for x in res]
            elif items:
                res = await bot.send_photo(m.tg_id, items[0])
                if res and getattr(res, "photo", None):
                    items = [res.photo[-1].file_id]
            await bot.send_location(m.tg_id, spot["lat"], spot["lon"])
            await bot.send_message(m.tg_id, card_text(spot, lang, author.fullname, author.username or ""),
                                   reply_markup=mod_kb(spot, lang), disable_web_page_preview=True)
            sent += 1
        except exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
        except exceptions.TelegramAPIError:
            pass
        await asyncio.sleep(0.05)
    return sent


def _map_kb(bot, lang, sid) -> InlineKeyboardMarkup | None:
    from tgbot.handlers.miniapp import app_url
    url = app_url(bot, spot=sid) if hasattr(bot, "get") and bot.get("config") else None
    return InlineKeyboardMarkup().add(InlineKeyboardButton(t("spot_btn_map", lang), web_app=WebAppInfo(url=url))) if url else None


async def notify_author(bot, s: dict, pts: int = 0, reason: str = "", event=None):
    """Автору — что стало с его сообщением (и «до / после», когда убрано)."""
    if not s.get("tg"):
        return
    lang = await lang_of(s["tg"])
    st = s["status"]
    try:
        if st == "cleaned":
            before = s["photos"][:1]
            after = s["after"][:3]
            if before and after:
                media = [InputMediaPhoto(_file(before[0]), caption=t("spot_before", lang))]
                media += [InputMediaPhoto(_file(x), caption=t("spot_after", lang) if i == 0 else None) for i, x in enumerate(after)]
                await bot.send_media_group(s["tg"], media)
        from app_telegram.spots import author_text
        text = author_text(s, pts, reason, event, lang)
        await bot.send_message(s["tg"], text, reply_markup=_map_kb(bot, lang, s["id"]) if st != "rejected" else None)
    except exceptions.TelegramAPIError:
        pass
    except Exception:
        log.exception("spot notify author")


async def mod_callback(call: types.CallbackQuery):
    from app_telegram import spots as SP
    parts = call.data.split(":")
    act, sid = parts[1], int(parts[2])
    me = await _user(call.from_user.id)
    s = await sync_to_async(SP.get)(sid)
    lang = await lang_of(call.from_user.id)
    if not s or not await sync_to_async(SP.can_moderate)(me, s):
        await call.answer(t("spot_m_denied", lang), show_alert=True)
        return
    allowed = {"a": ("new",), "r": ("new",), "rr": ("new",), "back": ("new",), "d": ("new",),
               "e": ("new", "accepted"), "c": ("new", "accepted", "planned")}
    if s["status"] not in allowed.get(act, ()):
        await call.answer(t("spot_m_already", lang, status=t(f"spot_st_{s['status']}", lang)), show_alert=True)
        try:
            await call.message.edit_reply_markup(mod_kb(s, lang))
        except exceptions.TelegramAPIError:
            pass
        return
    if act == "r":                                   # выбор причины
        kb = InlineKeyboardMarkup(row_width=1).add(
            *[InlineKeyboardButton(t(f"spot_rr_{r}", lang), callback_data=f"sm:rr:{sid}:{r}") for r in SP.REASONS],
            InlineKeyboardButton("⬅️", callback_data=f"sm:back:{sid}"))
        await call.answer()
        await call.message.edit_reply_markup(kb)
        return
    if act == "back":
        await call.answer()
        await call.message.edit_reply_markup(mod_kb(s, lang))
        return
    await call.answer()
    event, reason, pts = None, "", 0
    if act == "a":
        s, pts = await sync_to_async(SP.set_status)(sid, "accepted", call.from_user.id)
    elif act == "rr":
        reason = parts[3] if len(parts) > 3 and parts[3] in SP.REASONS else "other"
        s, pts = await sync_to_async(SP.set_status)(sid, "rejected", call.from_user.id, reason=reason)
    elif act == "d":
        s, pts = await sync_to_async(SP.set_status)(sid, "duplicate", call.from_user.id)
    elif act == "e":
        event, pts = await sync_to_async(SP.create_event)(sid, call.from_user.id)
        s = await sync_to_async(SP.get)(sid)
        from app_telegram.certificates import PUBLIC_URL
        await call.message.answer(t("spot_event_made", lang, title=escape(event.title), date=timezone.localtime(event.date).strftime("%d.%m %H:%M"),
                                    url=f"{PUBLIC_URL}/admin/app_telegram/ecoproject/{event.id}/change/"))
    elif act == "c":
        s, pts = await sync_to_async(SP.set_status)(sid, "cleaned", call.from_user.id)
    who = escape(me.fullname if me else str(call.from_user.id))
    try:
        await call.message.edit_text(call.message.html_text + "\n\n" + t("spot_m_done", lang, status=t(f"spot_st_{s['status']}", lang), who=who),
                                     reply_markup=mod_kb(s, lang), disable_web_page_preview=True)
    except exceptions.TelegramAPIError:
        pass
    await notify_author(call.bot, s, pts, reason, event)


async def notify_cleaned_by_event(bot, pid: int):
    """Итоги мероприятия внесены (/natija) → места, для которых оно было, — «убрано» + «до / после» авторам."""
    from app_telegram import spots as SP
    for s, pts in await sync_to_async(SP.on_event_results)(pid):
        await notify_author(bot, s, pts)


def register_spots_start(dp: Dispatcher):
    """t.me/<бот>?start=spot (кнопка в Mini App) — раньше общего /start."""
    dp.register_message_handler(spot_start, lambda m: m.get_args() == "spot", commands=["start"], state="*")


def register_spots(dp: Dispatcher):
    dp.register_message_handler(spot_start, commands=["iflos", "spot", "joy"], state="*")
    dp.register_message_handler(spot_start, text=variants("btn_spot"), state="*")
    dp.register_callback_query_handler(cancel_callback, text="spx", state="*")
    dp.register_callback_query_handler(next_callback, text="spn", state="*")
    dp.register_callback_query_handler(skip_note, text="spskip", state="*")
    dp.register_callback_query_handler(send_callback, text="spok", state="*")
    dp.register_callback_query_handler(details_callback, lambda c: c.data.split(":")[0] in ("spd", "spnew", "spr", "spro", "sps", "spk", "spa"), state="*")
    dp.register_callback_query_handler(mod_callback, lambda c: c.data.startswith("sm:"), state="*")
    dp.register_message_handler(photo_input, state=SpotStates.photos, content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT])
    dp.register_message_handler(photos_text, state=SpotStates.photos, content_types=types.ContentTypes.TEXT)
    dp.register_message_handler(location_input, state=SpotStates.location, content_types=[types.ContentType.LOCATION, types.ContentType.VENUE])
    dp.register_message_handler(location_text, state=SpotStates.location, content_types=types.ContentTypes.TEXT)
    dp.register_message_handler(note_input, state=SpotStates.note, content_types=types.ContentTypes.TEXT)
