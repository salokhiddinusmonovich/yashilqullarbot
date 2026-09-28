"""
👑 Отметка «пришёл» для админов (галочка is_admin) — без привязки к региону и к «сегодня».

Зачем: человек забыл показать QR на мероприятии и прислал его потом (скриншотом).
Координаторы сканируют как раньше: только свой регион, мероприятие выбирается само.
Админ:
  • открыл QR-ссылку (t.me/<бот>?start=qr_<id>) — бот спрашивает, на какое мероприятие отметить:
    ТОЛЬКО мероприятия региона человека (60 дней назад … 7 вперёд) — самаркандца на ташкентское нельзя
    (services.wrong_region); регион у человека не указан — все регионы;
  • переслал боту скриншот/фото QR — бот сам читает код (zxing-cpp) и спрашивает то же;
  • /belgila <имя, телефон или @username> — найти человека вообще без QR.
callback: qa:<tg>:<pid> — отметить, qu:<tg> — выбран человек.
"""
import logging
from datetime import timedelta
from html import escape
from io import BytesIO

from aiogram import types, Dispatcher
from aiogram.dispatcher.handler import SkipHandler
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import exceptions
from asgiref.sync import sync_to_async
from django.utils import timezone

from tgbot.i18n import t, region_label

log = logging.getLogger(__name__)


@sync_to_async
def _admin(tg: int):
    from app_telegram.models import TGUser
    u = TGUser.objects.filter(tg_id=tg).first()
    return u if u and u.is_admin else None


def read_qr(data: bytes) -> int | None:
    """tg_id из картинки с QR (скриншот, фото экрана) или None. Нет библиотеки — None."""
    from app_telegram import services
    try:
        import zxingcpp
        from PIL import Image, ImageOps
    except ImportError:
        log.warning("zxing-cpp не установлен — QR со скриншота не прочитать")
        return None
    try:
        with Image.open(BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            for img in (im, ImageOps.grayscale(im), ImageOps.invert(ImageOps.grayscale(im))):
                for r in zxingcpp.read_barcodes(img):
                    tg = services.parse_qr(r.text)
                    if tg:
                        return tg
    except Exception:
        log.exception("read qr")
    return None


@sync_to_async
def _events(target_tg: int, scope: str):
    from app_telegram import services
    from app_telegram.models import EcoProject, ProjectParticipation, TGUser
    v = TGUser.objects.filter(tg_id=target_tg).first()
    if not v:
        return None, []
    now = timezone.now()
    qs = EcoProject.objects.filter(date__gte=now - timedelta(days=services.ADMIN_BACK_DAYS), date__lte=now + timedelta(days=7))
    if v.region:                       # только его регион — чужой регион это ошибка (services.wrong_region)
        qs = qs.filter(region__in=services.region_group(v.region))
    evs = list(qs.order_by('-date')[:12])
    done = set(ProjectParticipation.objects.filter(user=v, project__in=evs, status='attended').values_list('project_id', flat=True))
    return v, [(p, p.id in done) for p in evs]


def _events_kb(target_tg: int, items, scope: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for p, done in items:
        d = timezone.localtime(p.date).strftime('%d.%m')
        reg = f" · {region_label(p.region)}" if scope == "a" else ""
        kb.add(InlineKeyboardButton(f"{'✅' if done else '📍'} {d} · {p.title[:34]}{reg}", callback_data=f"qa:{target_tg}:{p.id}"))
    return kb


async def admin_pick(chat: types.Message, target_tg: int, scope: str = "v", edit: bool = False):
    """Админу — «на какое мероприятие отметить <имя>?»."""
    v, items = await _events(target_tg, scope)
    if not v:
        await chat.answer(t("qr_user_not_found"))
        return
    scope = "v" if v.region else "a"          # без региона — показываем регион у каждого мероприятия
    text = t("ascan_pick", name=escape(v.fullname), region=region_label(v.region) if v.region else "—", days=60)
    if not items:
        text += "\n\n" + t("ascan_no_events")
    kb = _events_kb(target_tg, items, scope)
    if edit:
        try:
            await chat.edit_text(text, reply_markup=kb)
            return
        except exceptions.TelegramAPIError:
            pass
    await chat.answer(text, reply_markup=kb)


@sync_to_async
def _mark(target_tg: int, pid: int):
    from app_telegram import services
    from app_telegram.models import EcoProject, TGUser
    v = TGUser.objects.filter(tg_id=target_tg).first()
    p = EcoProject.objects.filter(id=pid).first()
    if not v or not p:
        return None, None, None, False
    if services.wrong_region(v, p):
        return v, p, "wrong_region", False
    result, auto_added = services.check_in(v, p)
    v.refresh_from_db(fields=['balance'])
    return v, p, result, auto_added


async def mark_callback(call: types.CallbackQuery):
    from tgbot.services.lang import lang_of
    from .feedback import ask_feedback
    me = await _admin(call.from_user.id)
    if not me:
        await call.answer(t("qr_no_rights"), show_alert=True)
        return
    _, tg, pid = call.data.split(":")
    v, p, result, auto_added = await _mark(int(tg), int(pid))
    if not v:
        await call.answer(t("qr_user_not_found"), show_alert=True)
        return
    if result == "wrong_region":
        await call.answer(t("qr_wrong_region_short", pregion=region_label(v.region), eregion=region_label(p.region)), show_alert=True)
        return
    await call.answer()
    when = timezone.localtime(p.date).strftime('%d.%m.%Y')
    if result == "already":
        text = t("ascan_already", name=escape(v.fullname), project=escape(p.title), date=when)
    else:
        text = t("ascan_ok", name=escape(v.fullname), project=escape(p.title), date=when, balance=v.balance,
                 note=t("qr_auto_added") if auto_added else "")
    try:
        await call.message.edit_text(text)
    except exceptions.TelegramAPIError:
        await call.message.answer(text)
    if result == "ok" and v.tg_id:
        try:
            await call.bot.send_message(v.tg_id, t("attended_notify", await lang_of(v.tg_id), project=escape(p.title), balance=v.balance))
            await ask_feedback(call.bot, v.tg_id, p.id, p.title)
        except Exception:
            pass


async def qr_photo(message: types.Message):
    """Админ прислал фото/скриншот: есть QR человека — спрашиваем мероприятие; нет — дальше, другим обработчикам."""
    if not await _admin(message.from_user.id):
        raise SkipHandler()
    buf = BytesIO()
    if message.photo:
        await message.photo[-1].download(destination_file=buf)
    elif message.document and (message.document.mime_type or "").startswith("image/"):
        await message.document.download(destination_file=buf)
    else:
        raise SkipHandler()
    tg = await sync_to_async(read_qr)(buf.getvalue())
    if not tg:
        raise SkipHandler()
    await admin_pick(message, tg)


@sync_to_async
def _find(q: str):
    from app_telegram import services
    from app_telegram.models import TGUser
    return list(TGUser.objects.filter(services.user_search_q(q), tg_id__isnull=False).order_by('fullname')[:10])


async def belgila_handler(message: types.Message):
    """/belgila <имя | телефон | @username> — отметить человека без QR."""
    if not await _admin(message.from_user.id):
        await message.answer(t("qr_no_rights"))
        return
    q = (message.get_args() or "").strip()
    if len(q) < 2:
        await message.answer(t("ascan_find_help"))
        return
    people = await _find(q)
    if not people:
        await message.answer(t("ascan_find_none", q=escape(q)))
        return
    kb = InlineKeyboardMarkup(row_width=1)
    for u in people:
        extra = f" · {region_label(u.region)}" if u.region else ""
        kb.add(InlineKeyboardButton(f"👤 {u.fullname[:36]}{extra}", callback_data=f"qu:{u.tg_id}"))
    await message.answer(t("ascan_find_pick", n=len(people)), reply_markup=kb)


async def user_callback(call: types.CallbackQuery):
    if not await _admin(call.from_user.id):
        await call.answer(t("qr_no_rights"), show_alert=True)
        return
    await call.answer()
    await admin_pick(call.message, int(call.data.split(":")[1]), edit=True)


def register_admin_scan(dp: Dispatcher):
    dp.register_message_handler(belgila_handler, commands=["belgila", "mark", "отметить"], state="*")
    dp.register_callback_query_handler(mark_callback, lambda c: c.data.startswith("qa:"), state="*")
    dp.register_callback_query_handler(user_callback, lambda c: c.data.startswith("qu:"), state="*")
    # только вне анкет/шагов (state=None): там фото — это ответ на вопрос, а не QR
    dp.register_message_handler(qr_photo, content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT], state=None)
