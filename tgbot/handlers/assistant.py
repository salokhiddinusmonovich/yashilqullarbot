"""
🤖 Помощник — бесплатно.

Волонтёрам: «❓ Qo'llanma» → «🤖 Savol berish» (или /ask) — режим вопросов.
  Сначала FAQ без ИИ (tgbot/services/faq.py), не нашёл — бесплатный Gemini
  (tgbot/services/ai.py, если есть GEMINI_API_KEY), не вышло — «напишите координатору».

Админам: /admin → «🎙 Buyruq» — команды текстом или голосом через микрофон
  клавиатуры (телефон сам превращает речь в текст — бесплатно):
  «bugun toshkent excel», «hafta statistika», «samarqand koordinatorlari»,
  «kelgusi tadbirlar», «top Aziza». Сначала правила (без ИИ), непонятное — Gemini
  переводит в команду. Только ЧТЕНИЕ: отчёты, цифры, поиск. Изменения
  (роли, рассылки) — по-прежнему кнопками, ИИ их не выполняет.
"""
import logging
import re
from datetime import timedelta
from html import escape

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from django.utils import timezone

from tgbot.i18n import t, variants, current_lang, region_label, role_label, REGIONS
from tgbot.keyboards import reply
from tgbot.services import ai, faq

log = logging.getLogger(__name__)


class AskState(StatesGroup):
    waiting = State()


# ═══════════════════════════ волонтёры ═══════════════════════════

def ask_kb():
    return ReplyKeyboardMarkup([[KeyboardButton(t("ask_exit_btn"))]], resize_keyboard=True)


def ask_inline():
    return InlineKeyboardMarkup().add(InlineKeyboardButton(t("ask_btn"), callback_data="ask:start"))


async def ask_start(message: types.Message, state: FSMContext):
    await state.finish()
    await AskState.waiting.set()
    await message.answer(t("ask_intro"), reply_markup=ask_kb())


async def ask_start_cb(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    await ask_start(call.message, state)


@sync_to_async
def _user_ctx(tg_id: int) -> tuple[str, bool]:
    """Данные человека для ИИ (только чтение) + is_admin для клавиатуры."""
    from app_telegram.models import TGUser, ProjectParticipation
    u = TGUser.objects.filter(tg_id=tg_id).first()
    if not u:
        return "Not registered in the bot yet.", False
    now = timezone.now()
    upcoming = ProjectParticipation.objects.filter(user=u, status__in=('approved', 'attended'),
                                                   project__date__gte=now - timedelta(hours=12)).select_related('project')
    ev = "; ".join(f"«{p.project.title}» {timezone.localtime(p.project.date):%d.%m %H:%M}" for p in upcoming[:5]) or "none"
    attended = ProjectParticipation.objects.filter(user=u, status='attended').count()
    return (f"Name: {u.fullname}. Region: {region_label(u.region, 'en') if u.region else 'not set'}. "
            f"Role: {role_label(u.role, 'en')}. Points: {u.balance}. Events attended: {attended}. "
            f"Registered upcoming events: {ev}."), bool(u.is_admin)


async def ask_question(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    lang = current_lang.get() or "uz"
    if not text:
        return
    if text in variants("ask_exit_btn") or text.startswith("/"):
        await state.finish()
        _, is_admin = await _user_ctx(message.from_user.id)
        await message.answer(t("ask_bye"), reply_markup=reply.hi_there(is_admin))
        return

    # 1) FAQ — бесплатно и без выдумок
    entry = faq.match(text)
    if entry:
        await message.answer(faq.answer(entry, lang), reply_markup=ask_kb())
        return

    # 2) бесплатный ИИ
    if ai.enabled():
        if not await ai.take_quota(message.from_user.id):
            await message.answer(t("ask_limit", n=ai.DAILY_LIMIT), reply_markup=ask_kb())
            return
        await message.bot.send_chat_action(message.chat.id, "typing")
        ctx, _ = await _user_ctx(message.from_user.id)
        data = await state.get_data()
        history = data.get("hist", [])
        try:
            answer = await ai.ask(text, lang, ctx, history)
        except ai.Unavailable as e:
            log.info("ai unavailable: %s", e)
        else:
            await state.update_data(hist=(history + [[text[:500], answer[:800]]])[-3:])
            await message.answer(answer + t("ask_ai_note"), reply_markup=ask_kb())
            return

    # 3) запасной ответ
    await message.answer(t("ask_fallback"), reply_markup=ask_kb())


async def ask_voice(message: types.Message):
    await message.answer(t("voice_tip"))


# ═══════════════════════════ команды админа ═══════════════════════════

PERIOD_WORDS = {
    "yesterday": ("kecha", "вчера", "yesterday", "кеча"),
    "week": ("hafta", "недел", "week", "haftalik"),
    "month": ("oylik", "oyda", "месяц", "month"),
    "all": ("hammasi", "umuman", "всё", "все время", "all time", "barcha vaqt"),
    "today": ("bugun", "сегодня", "today", "бугун"),
}
REGION_WORDS = {
    "tashkent": ("toshkent", "ташкент", "tashkent", "тошкент"),
    "samarkand": ("samarqand", "самарканд", "samarkand"),
    "andijon": ("andijon", "андижан", "andijan", "андижон"),
    "bukhara": ("buxoro", "бухар", "bukhara", "бухоро"),
    "fargona": ("farg'ona", "fargona", "фергана", "ферган", "fergana", "фаргона"),
    "jizzakh": ("jizzax", "джизак", "jizzakh", "жиззах"),
    "khorezm": ("xorazm", "хорезм", "khorezm", "urganch", "хоразм", "урганч"),
    "namangan": ("namangan", "наманган"),
    "navoi": ("navoiy", "навои", "navoi", "навоий"),
    "qashqadaryo": ("qashqadaryo", "кашкадар", "kashkadarya", "qarshi"),
    "sirdaryo": ("sirdaryo", "сырдар", "syrdarya", "guliston", "сирдарё"),
    "surkhandaryo": ("surxondaryo", "сурхандар", "surkhandarya", "termiz", "сурхондарё", "термиз"),
    "karakalpakstan": ("qoraqalpog", "каракалпак", "karakalpak", "nukus", "нукус"),
}
ACTION_WORDS = [   # порядок = приоритет
    ("report", ("excel", "эксель", "hisobot", "ҳисобот", "келган", "рўйхат", "kelgan", "keldi", "отчёт", "отчет", "пришл", "пришед", "report", "attend", "ro'yxat", "список")),
    ("coordinators", ("koordinator", "координатор", "coordinator", "jamoa", "команд", "team")),
    ("stats", ("statistika", "статистик", "нечта", "stats", "nechta", "сколько", "raqam", "цифр", "yangi")),
    ("events", ("tadbir", "мероприят", "event", "тадбир")),
    ("find", ("top", "qidir", "найди", "найти", "find", "search", "kim bu", "кто такой")),
]


def parse_rules(text: str) -> dict | None:
    s = faq.normalize(text)
    toks = faq.words(text)

    def has(words):
        return any((" " in w and w in s) or any(tk.startswith(w) for tk in toks) for w in words)

    action = next((a for a, w in ACTION_WORDS if has(w)), None)
    if action is None and re.search(r"@\w{3,}|\+?998\d{7,}|\b\d{9}\b", text):
        action = "find"
    if action is None:
        return None
    period = next((p for p, w in PERIOD_WORDS.items() if has(w)), "today")
    region = next((r for r, w in REGION_WORDS.items() if has(w)), "all")
    query = ""
    if action == "find":
        m = re.search(r"(?:top|qidir\w*|найд\w*|найти|find|search)\s+(.+)", text, re.I)
        query = (m.group(1) if m else text).strip()
    return {"action": action, "period": period, "region": region, "query": query}


async def cmd_message(message: types.Message, state: FSMContext):
    from .admin_panel import is_admin, send_report, search_users, _user_line, main_kb
    from app_telegram import reports

    if not await is_admin(message.bot, message.from_user.id):
        await state.finish()
        return
    text = (message.text or "").strip()
    if not text:
        return
    cmd = parse_rules(text)
    if cmd is None and ai.enabled():
        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
            cmd = await ai.parse_command(text, list(reports.REGION_CHOICES))
        except ai.Unavailable as e:
            log.info("ai cmd unavailable: %s", e)
    action = (cmd or {}).get("action", "unknown")
    period = cmd.get("period") if cmd and cmd.get("period") in reports.PERIODS else "today"
    region = cmd.get("region") if cmd and cmd.get("region") in reports.REGION_CHOICES else "all"
    again = InlineKeyboardMarkup().add(InlineKeyboardButton(t("adm_btn_menu"), callback_data="adm:menu"))

    if action == "report":
        await message.answer(t("cmd_doing", what=f"📋 {t(f'rep_p_{period}')} · {escape(reports.region_choice_label(region))}"))
        await send_report(message, message.from_user.id, period, region)
    elif action == "stats":
        await message.answer(await _stats_text(period, region), reply_markup=again)
    elif action == "coordinators":
        await message.answer(await _coordinators_text(region), reply_markup=again)
    elif action == "events":
        await message.answer(await _events_text(region), reply_markup=again)
    elif action == "find" and (cmd.get("query") or "").strip():
        users = await search_users(cmd["query"].strip())
        if not users:
            await message.answer(t("cmd_find_none", q=escape(cmd["query"])), reply_markup=again)
            return
        kb = InlineKeyboardMarkup(row_width=1)
        for u in users:
            kb.add(InlineKeyboardButton(_user_line(u)[:60], callback_data=f"adm:u:{u.id}"))
        kb.add(InlineKeyboardButton(t("adm_btn_menu"), callback_data="adm:menu"))
        await message.answer(t("cmd_found", n=len(users)), reply_markup=kb)
    else:
        await message.answer(t("cmd_unknown"), reply_markup=again)


async def cmd_voice(message: types.Message):
    await message.answer(t("voice_tip"))


@sync_to_async
def _stats_text(period, region):
    from app_telegram import reports
    from app_telegram.models import TGUser, EcoProject, ProjectParticipation
    d_from, d_to = reports.period_range(period)
    regions = reports.region_codes(region)
    users = TGUser.objects.all()
    parts = ProjectParticipation.objects.filter(status='attended')
    events = EcoProject.objects.all()
    if d_from:
        users = users.filter(created__date__gte=d_from, created__date__lte=d_to)
        parts = parts.filter(project__date__date__gte=d_from, project__date__date__lte=d_to)
        events = events.filter(date__date__gte=d_from, date__date__lte=d_to)
    if regions:
        users = users.filter(region__in=regions)
        parts = parts.filter(project__region__in=regions)
        events = events.filter(region__in=regions)
    return t("cmd_stats", period=t(f"rep_p_{period}"), region=escape(reports.region_choice_label(region)),
             new=users.count(), att=parts.count(), people=parts.values('user').distinct().count(),
             events=events.count(), total=TGUser.objects.filter(region__in=regions).count() if regions else TGUser.objects.count())


@sync_to_async
def _coordinators_text(region):
    from app_telegram import reports
    from app_telegram.models import TGUser
    qs = TGUser.objects.exclude(role=TGUser.Role.VOLUNTEER)
    regions = reports.region_codes(region)
    if regions:
        qs = qs.filter(region__in=regions)
    qs = list(qs.order_by('region', 'role', 'fullname')[:60])
    if not qs:
        return t("cmd_none")
    lines = [t("cmd_coord_title", region=escape(reports.region_choice_label(region)), n=len(qs)), ""]
    for u in qs:
        contact = " · ".join(x for x in (f"@{u.username}" if u.username else "", u.phone or "") if x)
        lines.append(f"• <b>{escape(u.fullname or '—')}</b> — {role_label(u.role)}"
                     + (f", {region_label(u.region)}" if not regions and u.region else "")
                     + (f"\n   {escape(contact)}" if contact else ""))
    return "\n".join(lines)[:4000]


@sync_to_async
def _events_text(region):
    from app_telegram import reports
    from app_telegram.models import EcoProject
    now = timezone.now()
    qs = EcoProject.objects.filter(date__gte=now - timedelta(hours=6), date__lte=now + timedelta(days=30))
    regions = reports.region_codes(region)
    if regions:
        qs = qs.filter(region__in=regions)
    qs = list(qs.annotate(
        registered=Count('participants', filter=~Q(participants__status='rejected')),
        attended=Count('participants', filter=Q(participants__status='attended')),
    ).order_by('date')[:25])
    if not qs:
        return t("cmd_none")
    lines = [t("cmd_events_title", region=escape(reports.region_choice_label(region)), n=len(qs)), ""]
    for e in qs:
        lines.append(f"📅 {timezone.localtime(e.date):%d.%m %H:%M} · <b>{escape(e.title)}</b>\n"
                     f"   📍 {region_label(e.region) if e.region else '—'} · 👥 {e.registered} · ✅ {e.attended}")
    return "\n".join(lines)[:4000]


def register_assistant(dp: Dispatcher):
    from .admin_panel import AdminStates
    dp.register_message_handler(ask_start, commands=["ask"], state="*")
    dp.register_message_handler(ask_start, text=variants("ask_btn"), state="*")
    dp.register_callback_query_handler(ask_start_cb, text="ask:start", state="*")
    dp.register_message_handler(ask_voice, content_types=types.ContentType.VOICE, state=AskState.waiting)
    dp.register_message_handler(ask_question, state=AskState.waiting)
    dp.register_message_handler(cmd_voice, content_types=types.ContentType.VOICE, state=AdminStates.command)
    dp.register_message_handler(cmd_message, state=AdminStates.command)
