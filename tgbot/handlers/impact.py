"""
📊 Итоги мероприятия — координатор вводит в боте: кг мусора → мешки → деревья → фото.

/natija — список прошедших мероприятий своего региона (✅ — итоги уже есть).
Кнопка «📊 Natijalarni kiritish» приходит и сама, через ~3 часа после начала мероприятия
(tgbot/services/impact_prompt.py). Любой шаг можно пропустить — останется прежнее значение.
Как только впервые появились цифры, каждому, кто пришёл, бот пишет «вместе мы собрали …,
ваша доля ≈ …» (один раз на мероприятие).
"""
import asyncio
import logging
import re
from html import escape
from io import BytesIO

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from django.utils import timezone

from tgbot.i18n import t
from tgbot.services.lang import _aclient, langs_of

log = logging.getLogger(__name__)
STEPS = ("kg", "bags", "trees")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


class ImpactStates(StatesGroup):
    kg = State()
    bags = State()
    trees = State()
    photos = State()


@sync_to_async
def _staff(tg_id: int):
    from app_telegram import services
    from app_telegram.models import TGUser
    u = TGUser.objects.filter(tg_id=tg_id).first()
    return u if u and services.is_staff(u) else None


@sync_to_async
def _events_for(user):
    from app_telegram import impact
    evs = impact.recent_for_staff(user)
    done = impact.many([e.id for e in evs])
    return [(e, e.id in done) for e in evs]


@sync_to_async
def _project_for(tg_id: int, pid: int):
    """Мероприятие, если этот человек может вводить его итоги (координатор своего региона)."""
    from app_telegram import services
    from app_telegram.models import EcoProject, TGUser
    u = TGUser.objects.filter(tg_id=tg_id).first()
    p = EcoProject.objects.filter(id=pid).first()
    if not u or not p or not services.is_staff(u) or not services.can_scan_project(u, p):
        return None
    return p


def _label(p) -> str:
    return f"{timezone.localtime(p.date).strftime('%d.%m')} · {p.title[:42]}"


async def natija_handler(message: types.Message, state: FSMContext):
    user = await _staff(message.from_user.id)
    if not user:
        await message.answer(t("imp_staff_only"))
        return
    await state.finish()
    items = await _events_for(user)
    if not items:
        await message.answer(t("imp_no_events"))
        return
    kb = InlineKeyboardMarkup(row_width=1)
    for p, done in items:
        kb.add(InlineKeyboardButton(f"{'✅' if done else '📊'} {_label(p)}", callback_data=f"imp:{p.id}"))
    await message.answer(t("imp_pick"), reply_markup=kb)


def _step_kb(has_photos=False, last=False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    if last:
        kb.add(InlineKeyboardButton(t("imp_btn_done"), callback_data="impd"))
        if has_photos:
            kb.add(InlineKeyboardButton(t("imp_btn_clear"), callback_data="impclr"))
    else:
        kb.add(InlineKeyboardButton(t("imp_btn_skip"), callback_data="imps"))
    kb.add(InlineKeyboardButton(t("imp_btn_cancel"), callback_data="impx"))
    return kb


async def _ask(chat: types.Message, state: FSMContext, step: str):
    """Показать вопрос шага (kg / bags / trees / photos)."""
    from app_telegram import impact
    data = await state.get_data()
    cur = await sync_to_async(impact.get)(data["pid"])
    head = t("imp_head", title=escape(data["title"]))
    if step == "photos":
        n = len(cur.get("photos", []))
        await ImpactStates.photos.set()
        await chat.answer(f"{head}\n\n{t('imp_q_photos', n=n)}", reply_markup=_step_kb(has_photos=n > 0, last=True))
        return
    await getattr(ImpactStates, step).set()
    now = t("imp_now", v=impact._fmt(cur[step])) if cur.get(step) else ""
    await chat.answer(f"{head}\n\n{t(f'imp_q_{step}')}{now}", reply_markup=_step_kb())


async def start_callback(call: types.CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    p = await _project_for(call.from_user.id, pid)
    if not p:
        await call.answer(t("imp_staff_only"), show_alert=True)
        return
    await call.answer()
    await state.finish()
    await state.update_data(pid=p.id, title=p.title, vals={})
    await _ask(call.message, state, "kg")


def _next(step: str) -> str:
    i = STEPS.index(step)
    return STEPS[i + 1] if i + 1 < len(STEPS) else "photos"


async def number_input(message: types.Message, state: FSMContext):
    step = (await state.get_state()).split(":")[-1]
    m = NUM_RE.search(message.text or "")
    if not m:
        await message.answer(t("imp_bad_num"))
        return
    v = float(m.group().replace(",", "."))
    if v > 1_000_000:
        await message.answer(t("imp_bad_num"))
        return
    data = await state.get_data()
    vals = {**data.get("vals", {}), step: v}
    await state.update_data(vals=vals)
    await _ask(message, state, _next(step))


async def skip_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    st = await state.get_state()
    if not st or not st.startswith("ImpactStates:"):
        return
    step = st.split(":")[-1]
    if step in STEPS:
        await _ask(call.message, state, _next(step))


async def cancel_callback(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await state.finish()
    await call.message.answer(t("imp_cancelled"))


async def photo_input(message: types.Message, state: FSMContext):
    from app_telegram import impact
    data = await state.get_data()
    buf = BytesIO()
    try:
        if message.photo:
            await message.photo[-1].download(destination_file=buf)
        elif message.document and (message.document.mime_type or "").startswith("image/"):
            await message.document.download(destination_file=buf)
        else:
            return
        rel = await sync_to_async(impact.add_photo)(data["pid"], buf.getvalue())
    except Exception:
        log.exception("impact photo")
        await message.answer(t("imp_photo_err"))
        return
    if rel is None:
        await message.answer(t("imp_photo_max", n=impact.MAX_PHOTOS))
        return
    # альбом приходит пачкой сообщений — отвечаем один раз на альбом
    mg = message.media_group_id
    if mg and data.get("mg") == mg:
        return
    await state.update_data(mg=mg)
    await message.answer(t("imp_photo_ok"), reply_markup=_step_kb(last=True))


async def photos_text(message: types.Message):
    await message.answer(t("imp_photo_hint"), reply_markup=_step_kb(last=True))


async def clear_callback(call: types.CallbackQuery, state: FSMContext):
    from app_telegram import impact
    data = await state.get_data()
    if not data.get("pid"):
        await call.answer()
        return
    await sync_to_async(impact.clear_photos)(data["pid"])
    await call.answer(t("imp_cleared"), show_alert=True)


async def done_callback(call: types.CallbackQuery, state: FSMContext):
    from app_telegram import impact
    data = await state.get_data()
    await call.answer()
    if not data.get("pid"):
        return
    pid = data["pid"]
    had = impact.has_numbers(await sync_to_async(impact.get)(pid))
    await sync_to_async(impact.save)(pid, by_tg=call.from_user.id, **data.get("vals", {}))
    await state.finish()
    res = await sync_to_async(impact.get)(pid)
    text = t("imp_saved", title=escape(data["title"]), summary=impact.summary(res) or "—", n=len(res.get("photos", [])))
    await call.message.answer(text)
    # впервые появились цифры — поблагодарить всех, кто пришёл
    if not had and impact.has_numbers(res):
        asyncio.create_task(notify_volunteers(call.bot, pid))


@sync_to_async
def _volunteers(pid: int):
    from app_telegram import impact
    from app_telegram.models import EcoProject, ProjectParticipation
    p = EcoProject.objects.filter(id=pid).first()
    tgs = list(ProjectParticipation.objects.filter(project_id=pid, status='attended', user__tg_id__isnull=False)
               .values_list('user__tg_id', flat=True))
    return p, tgs, impact.get(pid)


async def notify_volunteers(bot, pid: int) -> int:
    """«Вместе мы собрали …, ваша доля ≈ …» — каждому, кто пришёл. Один раз на мероприятие."""
    from app_telegram import impact
    r = _aclient()
    try:
        if not await r.set(f"imp:notified:{pid}", 1, nx=True, ex=365 * 86400):
            return 0
    except Exception:
        return 0
    p, tgs, res = await _volunteers(pid)
    if not p or not tgs:
        return 0
    n = len(tgs)
    share = {k: (res[k] / n if res.get(k) else 0) for k in impact.KINDS}
    langs = await langs_of(tgs)
    cfg = bot.get("config") if hasattr(bot, "get") else None
    url = cfg.misc.miniapp_url if cfg else None
    sent = 0
    for tg in tgs:
        lang = langs.get(tg)
        mine = " · ".join(t(f"imp_u_{k}", lang, n=_approx(share[k])) for k in impact.KINDS if share[k])
        text = t("imp_thanks", lang, title=escape(p.title), summary=impact.summary(res, lang), n=n, mine=mine)
        kb = None
        if url:
            kb = InlineKeyboardMarkup().add(InlineKeyboardButton(t("imp_btn_photos", lang), web_app=WebAppInfo(url=f"{url}/?impact={pid}")))
        try:
            await bot.send_message(tg, text, reply_markup=kb)
            sent += 1
        except exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
        except exceptions.TelegramAPIError:
            pass
        await asyncio.sleep(0.05)
    return sent


def _approx(v: float) -> str:
    return f"≈{v:.1f}".rstrip("0").rstrip(".") if v < 10 else f"≈{round(v)}"


def register_impact(dp: Dispatcher):
    dp.register_message_handler(natija_handler, commands=["natija", "itog", "results", "итоги"], state="*")
    dp.register_callback_query_handler(start_callback, lambda c: c.data.startswith("imp:"), state="*")
    dp.register_callback_query_handler(skip_callback, text="imps", state="*")
    dp.register_callback_query_handler(cancel_callback, text="impx", state="*")
    dp.register_callback_query_handler(done_callback, text="impd", state="*")
    dp.register_callback_query_handler(clear_callback, text="impclr", state="*")
    dp.register_message_handler(number_input, state=[ImpactStates.kg, ImpactStates.bags, ImpactStates.trees],
                                content_types=types.ContentTypes.TEXT)
    dp.register_message_handler(photo_input, state=ImpactStates.photos,
                                content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT])
    dp.register_message_handler(photos_text, state=ImpactStates.photos, content_types=types.ContentTypes.TEXT)
