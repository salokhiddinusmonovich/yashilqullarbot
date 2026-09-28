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
    """Сразу к сообщению о новом месте (t.me/<бот>?start=spot из Mini App)."""
    await _begin(message, message.from_user.id, state)


async def _begin(chat: types.Message, tg: int, state: FSMContext):
    from app_telegram import spots as SP
    user = await _user(tg)
    if not user:
        await chat.answer(t("spot_register"))
        return
    if not await sync_to_async(SP.can_report)(tg):
        await chat.answer(t("spot_limit", n=SP.PER_DAY))
        return
    await state.finish()
    await _aclient().delete(_draft(tg))
    await SpotStates.photos.set()
    await chat.answer(t("spot_intro"), reply_markup=ReplyKeyboardRemove())
    await chat.answer(t("spot_q_photos"), reply_markup=_cancel_kb())


# ─────────── 🗺 эко-карта в боте (текстовый режим): меню и карточки мест ───────────
# «📍 Iflos joy» в меню → сводка по своему региону + списки: грязно / в планах / убрано / мои.
# Карточка — фото места, подпись и кнопки: ⬅️ ➡️, точка на карте, «до / после», «всё ещё грязно»,
# «записаться на уборку» (тот же evreg:, что и в меню мероприятий).
# callback: sph:<r|a> — меню (свой регион / вся страна), sphn — новое сообщение,
#           spv:<d|p|c|m>:<r|a>:<i> — карточка, spl:<id> — точка, spba:<id> — до/после, spc:<id> — «всё ещё грязно».

LIST_STATUS = {"d": ("accepted",), "p": ("planned",), "c": ("cleaned",)}


@sync_to_async
def _hub_data(tg: int, scope: str):
    from app_telegram import services, spots as SP
    from app_telegram.models import TGUser
    user = TGUser.objects.filter(tg_id=tg).first()
    group = services.region_group(user.region) if user and user.region else []
    items = [s for s in SP.all_spots() if SP.visible_to(s, user)]
    in_scope = [s for s in items if scope == "a" or not group or s.get("region") in group]
    n = lambda st: sum(1 for s in in_scope if s["status"] == st)
    mine = sum(1 for s in items if user and s.get("uid") == user.id)
    return user, group, {"d": n("accepted"), "p": n("planned"), "c": n("cleaned"), "m": mine}


def _hub_kb(bot, scope: str, c: dict) -> InlineKeyboardMarkup:
    from tgbot.handlers.miniapp import app_url
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(t("spot_btn_new"), callback_data="sphn"))
    kb.add(InlineKeyboardButton(t("spot_btn_dirty", n=c["d"]), callback_data=f"spv:d:{scope}:0"),
           InlineKeyboardButton(t("spot_btn_planned", n=c["p"]), callback_data=f"spv:p:{scope}:0"))
    kb.add(InlineKeyboardButton(t("spot_btn_cleaned", n=c["c"]), callback_data=f"spv:c:{scope}:0"),
           InlineKeyboardButton(t("spot_btn_mine", n=c["m"]), callback_data="spv:m:a:0"))
    kb.add(InlineKeyboardButton(t("spot_btn_scope_region") if scope == "a" else t("spot_btn_scope_all"),
                                callback_data=f"sph:{'r' if scope == 'a' else 'a'}"))
    url = app_url(bot, map=1) if hasattr(bot, "get") and bot.get("config") else None
    if url:
        kb.add(InlineKeyboardButton(t("spot_btn_openmap"), web_app=WebAppInfo(url=url)))
    return kb


async def spot_hub(message: types.Message, state: FSMContext):
    await state.finish()
    await _send_hub(message, message.from_user.id, "r")


async def _send_hub(chat: types.Message, tg: int, scope: str, edit: bool = False):
    user, group, c = await _hub_data(tg, scope)
    if not user:
        await chat.answer(t("spot_register"))
        return
    where = t("spot_hub_all") if scope == "a" or not group else region_label(user.region)
    text = t("spot_hub", scope=where, d=c["d"], p=c["p"], c=c["c"])
    kb = _hub_kb(chat.bot, scope, c)
    if edit:
        try:
            await chat.edit_text(text, reply_markup=kb)
            return
        except exceptions.TelegramAPIError:
            pass
    await chat.answer(text, reply_markup=kb)


async def hub_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    if call.data == "sphn":
        await _begin(call.message, call.from_user.id, state)
        return
    scope = call.data.split(":")[1] if ":" in call.data else "r"
    if call.message.photo:                      # из карточки «⬅️ Menyu» — карточку убираем, меню — новым сообщением
        try:
            await call.message.delete()
        except exceptions.TelegramAPIError:
            pass
        await _send_hub(call.message, call.from_user.id, scope)
    else:
        await _send_hub(call.message, call.from_user.id, scope, edit=True)


@sync_to_async
def _list(tg: int, f: str, scope: str):
    from app_telegram import services, spots as SP
    from app_telegram.models import EcoProject, TGUser
    user = TGUser.objects.filter(tg_id=tg).first()
    if not user:
        return None, []
    if f == "m":
        return user, [s for s in SP.all_spots() if s.get("uid") == user.id]
    group = services.region_group(user.region) if user.region else []
    items = [s for s in SP.all_spots(LIST_STATUS[f]) if scope == "a" or not group or s.get("region") in group]
    for s in items:
        s["_event"] = EcoProject.objects.filter(id=s["event_id"]).first() if s.get("event_id") else None
    return user, items


async def _photo(rel: str):
    """Фото места для карточки: уменьшенная копия с диска; file_id запоминаем — второй раз не грузим."""
    from pathlib import Path
    from django.conf import settings
    from app_telegram.thumbs import thumb_rel_url
    r = _aclient()
    fid = await r.get(f"spot:fid:{rel}")
    if fid:
        return fid
    await sync_to_async(thumb_rel_url)(rel, 1000)
    return InputFile(str(Path(settings.MEDIA_ROOT) / "thumbs" / "1000" / Path(rel).with_suffix(".jpg")))


def _card(s: dict, i: int, n: int, viewer, nav: str) -> tuple[str, InlineKeyboardMarkup]:
    """Подпись и кнопки карточки места. nav — начало callback для ⬅️ ➡️ (spv:<список>:<охват>)."""
    from app_telegram.spots import maps_links
    ev = s.get("_event")
    lines = [t("spot_view", id=s["id"], status=t(f"spot_st_{s['status']}"),
               region=region_label(s["region"]) if s.get("region") else "—",
               address=f" · {escape(s['address'])}" if s.get("address") else "",
               size=t(f"spot_size_{s['size']}"), kind=t(f"spot_kind_{s['kind']}"),
               date=timezone.localtime(datetime.fromtimestamp(s["created"], tz=dt_tz.utc)).strftime("%d.%m.%Y"),
               confirms=s.get("confirms", 0) + 1)]
    if s.get("note"):
        lines.append(f"✍️ {escape(s['note'])}")
    if ev:
        lines.append(t("spot_ev_line", title=escape(ev.title), date=timezone.localtime(ev.date).strftime("%d.%m %H:%M"))
                     + ("" if ev.is_active else t("spot_ev_soon")))
    kb = InlineKeyboardMarkup(row_width=3)
    if n > 1:
        kb.add(InlineKeyboardButton("⬅️", callback_data=f"{nav}:{max(i - 1, 0)}"),
               InlineKeyboardButton(f"{i + 1} / {n}", callback_data="noop"),
               InlineKeyboardButton("➡️", callback_data=f"{nav}:{min(i + 1, n - 1)}"))
    kb.row(InlineKeyboardButton(t("spot_btn_loc"), callback_data=f"spl:{s['id']}"),
           InlineKeyboardButton("🧭 Google Maps", url=maps_links(s["lat"], s["lon"])["google"]))
    if s["status"] == "cleaned" and s.get("after"):
        kb.row(InlineKeyboardButton(t("spot_btn_ba"), callback_data=f"spba:{s['id']}"))
    if ev and ev.is_active and ev.date > timezone.now():
        kb.row(InlineKeyboardButton(t("spot_btn_join"), callback_data=f"evreg:{ev.id}"))
    if s["status"] in ("accepted", "planned") and not (viewer and s.get("uid") == viewer.id):
        kb.row(InlineKeyboardButton(t("spot_btn_still"), callback_data=f"spc:{s['id']}"))
    kb.row(InlineKeyboardButton(t("spot_btn_menu"), callback_data="sph:r"))
    return "\n".join(lines), kb


async def view_callback(call: types.CallbackQuery):
    _, f, scope, i = call.data.split(":")
    user, items = await _list(call.from_user.id, f, scope)
    if not items:
        await call.answer(t("spot_empty"), show_alert=True)
        return
    await call.answer()
    i = max(0, min(int(i), len(items) - 1))
    s = items[i]
    caption, kb = _card(s, i, len(items), user, f"spv:{f}:{scope}")
    photo = await _photo(s["photos"][0]) if s["photos"] else None
    try:
        if call.message.photo and photo:            # листаем — меняем фото в той же карточке
            msg = await call.message.edit_media(InputMediaPhoto(photo, caption=caption), reply_markup=kb)
        elif photo:
            msg = await call.message.answer_photo(photo, caption=caption, reply_markup=kb)
        else:
            msg = await call.message.answer(caption, reply_markup=kb)
        if photo and not isinstance(photo, str) and getattr(msg, "photo", None):
            await _aclient().set(f"spot:fid:{s['photos'][0]}", msg.photo[-1].file_id, ex=30 * 86400)
    except exceptions.MessageNotModified:
        pass
    except exceptions.TelegramAPIError:
        log.exception("spot card")


@sync_to_async
def _spot(sid: int):
    from app_telegram import spots as SP
    return SP.get(sid)


async def location_callback(call: types.CallbackQuery):
    s = await _spot(int(call.data.split(":")[1]))
    await call.answer()
    if s:
        await call.message.answer_location(s["lat"], s["lon"])


async def before_after_callback(call: types.CallbackQuery):
    s = await _spot(int(call.data.split(":")[1]))
    await call.answer()
    if not s or not s["photos"] or not s["after"]:
        return
    media = [InputMediaPhoto(_file(s["photos"][0]), caption=t("spot_before"))]
    media += [InputMediaPhoto(_file(x), caption=t("spot_after") if k == 0 else None) for k, x in enumerate(s["after"][:3])]
    await call.message.answer_media_group(media)


async def still_dirty_callback(call: types.CallbackQuery):
    from app_telegram import spots as SP
    sid = int(call.data.split(":")[1])
    s = await _spot(sid)
    user = await _user(call.from_user.id)
    if not s or s["status"] not in SP.OPEN:
        await call.answer()
        return
    if user and s.get("uid") == user.id:
        await call.answer(t("spot_confirm_own"), show_alert=True)
        return
    n = await sync_to_async(SP.confirm)(sid, call.from_user.id)
    await call.answer(t("spot_confirm_ok", n=n + 1), show_alert=True)


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


def _map_kb(bot, lang, sid) -> InlineKeyboardMarkup:
    """Автору: «📍 Посмотреть» — карточка места прямо в боте; если есть Mini App — ещё и на эко-карте."""
    from tgbot.handlers.miniapp import app_url
    kb = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton(t("spot_btn_view", lang), callback_data=f"spo:{sid}"))
    url = app_url(bot, spot=sid) if hasattr(bot, "get") and bot.get("config") else None
    if url:
        kb.add(InlineKeyboardButton(t("spot_btn_map", lang), web_app=WebAppInfo(url=url)))
    return kb


@sync_to_async
def _one(tg: int, sid: int):
    from app_telegram import spots as SP
    from app_telegram.models import EcoProject, TGUser
    user = TGUser.objects.filter(tg_id=tg).first()
    s = SP.get(sid)
    if not s or not (SP.visible_to(s, user) or SP.can_moderate(user)):
        return user, None
    s["_event"] = EcoProject.objects.filter(id=s["event_id"]).first() if s.get("event_id") else None
    return user, s


async def one_callback(call: types.CallbackQuery):
    """spo:<id> — одна карточка места (из уведомления автору)."""
    user, s = await _one(call.from_user.id, int(call.data.split(":")[1]))
    if not s:
        await call.answer(t("spot_empty"), show_alert=True)
        return
    await call.answer()
    caption, kb = _card(s, 0, 1, user, f"spo:{s['id']}")
    photo = await _photo(s["photos"][0]) if s["photos"] else None
    if photo:
        msg = await call.message.answer_photo(photo, caption=caption, reply_markup=kb)
        if not isinstance(photo, str) and getattr(msg, "photo", None):
            await _aclient().set(f"spot:fid:{s['photos'][0]}", msg.photo[-1].file_id, ex=30 * 86400)
    else:
        await call.message.answer(caption, reply_markup=kb)


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
    # «📍 Iflos joy» и /iflos — меню эко-карты (там же «сообщить о новом месте»); /start spot — сразу сообщение
    dp.register_message_handler(spot_hub, commands=["iflos", "spot", "joy", "xarita", "map"], state="*")
    dp.register_message_handler(spot_hub, text=variants("btn_spot"), state="*")
    dp.register_callback_query_handler(hub_callback, lambda c: c.data == "sphn" or c.data.startswith("sph:"), state="*")
    dp.register_callback_query_handler(view_callback, lambda c: c.data.startswith("spv:"), state="*")
    dp.register_callback_query_handler(one_callback, lambda c: c.data.startswith("spo:"), state="*")
    dp.register_callback_query_handler(location_callback, lambda c: c.data.startswith("spl:"), state="*")
    dp.register_callback_query_handler(before_after_callback, lambda c: c.data.startswith("spba:"), state="*")
    dp.register_callback_query_handler(still_dirty_callback, lambda c: c.data.startswith("spc:"), state="*")
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
