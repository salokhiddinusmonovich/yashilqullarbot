"""
Бесплатный ИИ-помощник — Google Gemini (бесплатный тариф Google AI Studio).

Включается, только если в .env есть GEMINI_API_KEY (ключ бесплатный:
aistudio.google.com → Get API key). Без ключа бот отвечает только из FAQ.

Защита бесплатного лимита:
  • сначала FAQ (tgbot/services/faq.py) — ИИ зовём только если он не нашёл ответ;
  • на человека — AI_DAILY_LIMIT вопросов в день (по умолчанию 15), счётчик в Redis;
  • Google ответил 429 (лимит) — 2 минуты вообще не ходим в ИИ, отвечаем «напишите координатору».
Ответ только по справочнику (FAQ + инструкция) и данным самого человека — ничего не выдумывает.
"""
import asyncio
import json
import logging
import os
from datetime import date

import aiohttp

from . import faq
from .lang import _aclient

log = logging.getLogger(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "").strip()
# Имена моделей у Google меняются — пробуем по очереди, рабочую запоминаем (_working)
MODELS = [m for m in dict.fromkeys([MODEL, "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-flash-latest"]) if m]
_working = None
LAST_ERROR = ""
DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "15"))
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
LANG_NAMES = {"uz": "Uzbek (Latin script)", "ru": "Russian", "en": "English"}


def enabled() -> bool:
    return bool(API_KEY)


class Unavailable(Exception):
    """ИИ сейчас недоступен (нет ключа, лимит Google, сеть) — отвечаем запасным текстом."""


async def _cooling() -> bool:
    try:
        return bool(await _aclient().exists("ai:cooldown"))
    except Exception:
        return False


async def _cool_down(seconds=120):
    try:
        await _aclient().set("ai:cooldown", 1, ex=seconds)
    except Exception:
        pass


async def take_quota(tg_id: int) -> bool:
    """Списать один вопрос из дневного лимита человека. False — лимит исчерпан."""
    key = f"ai:q:{tg_id}:{date.today().isoformat()}"
    try:
        r = _aclient()
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, 26 * 3600)
        return n <= DAILY_LIMIT
    except Exception:
        return True   # Redis лёг — не наказываем человека


async def _post(model: str, body: dict):
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=40)) as s:
        async with s.post(URL.format(model=model), json=body, headers={"x-goog-api-key": API_KEY}) as resp:
            return resp.status, await resp.json(content_type=None)


def _retry_delay(data) -> float:
    """Сколько Google просит подождать при 429 (RetryInfo.retryDelay, «13s»)."""
    try:
        for d in data.get("error", {}).get("details", []):
            if "retryDelay" in d:
                return float(str(d["retryDelay"]).rstrip("s"))
    except (AttributeError, ValueError, TypeError):
        pass
    return 30.0


def _extract(data) -> tuple[str, str]:
    """(текст, finishReason). Мысли модели (thought) пропускаем."""
    try:
        cand = data["candidates"][0]
    except (KeyError, IndexError, TypeError):
        return "", "NO_CANDIDATE"
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    return text, cand.get("finishReason", "")


def _body(system, contents, json_mode, max_tokens, model, thinking_off=True):
    cfg = {"temperature": 0.2 if json_mode else 0.4, "maxOutputTokens": max_tokens}
    if json_mode:
        cfg["responseMimeType"] = "application/json"
    # Gemini 2.5 по умолчанию «думает» и может потратить на это весь лимит ответа (MAX_TOKENS, пустой ответ).
    # Нам размышления не нужны — выключаем: быстрее, дешевле для бесплатного лимита.
    if thinking_off and "2.5" in model:
        cfg["thinkingConfig"] = {"thinkingBudget": 0}
    return {"system_instruction": {"parts": [{"text": system}]}, "contents": contents, "generationConfig": cfg}


async def _generate(system: str, contents: list, json_mode=False, max_tokens=4096) -> str:
    """
    Запрос к Gemini. Модели пробуем по очереди: у каждой СВОЙ бесплатный лимит,
    поэтому 429 у одной — не повод сдаваться. Короткое «подождите N сек» (≤ 12) — ждём.
    Пустой ответ (обрезан/только мысли) — ещё раз без размышлений и с большим запасом, потом другая модель.
    Все модели на лимите — пауза и честное «ИИ занят» (Unavailable("rate limit")).
    """
    global _working, LAST_ERROR
    if not API_KEY:
        LAST_ERROR = "GEMINI_API_KEY yo'q (.env)"
        raise Unavailable("no key")
    if await _cooling():
        raise Unavailable("rate limit")
    order = ([_working] if _working else []) + [m for m in MODELS if m != _working]
    limited, wait_max = False, 0.0
    for model in order:
        thinking_off, tokens = True, max_tokens
        for attempt in range(3):
            try:
                status, data = await _post(model, _body(system, contents, json_mode, tokens, model, thinking_off))
            except (aiohttp.ClientError, TimeoutError) as e:
                LAST_ERROR = f"network: {e}"
                raise Unavailable(str(e))
            msg = (data or {}).get("error", {}).get("message", "") if isinstance(data, dict) else str(data)
            if status == 200:
                text, finish = _extract(data)
                if text:
                    _working = model
                    return text
                LAST_ERROR = f"{model}: empty answer ({finish})"
                log.warning("gemini %s", LAST_ERROR)
                tokens = min(tokens * 2, 8192)      # обрезало — больше места и ещё раз
                continue
            if status == 400 and "thinking" in msg.lower() and thinking_off:
                thinking_off = False                 # модель не знает thinkingConfig — без него
                continue
            LAST_ERROR = f"{model}: HTTP {status} {msg[:200]}"
            log.warning("gemini %s", LAST_ERROR)
            if status == 429:
                delay = _retry_delay(data)
                wait_max = max(wait_max, delay)
                if attempt == 0 and delay <= 12:
                    await asyncio.sleep(delay + 0.5)
                    continue
                limited = True
                break                                # у другой модели — свой лимит
            if status in (400, 403) and "API key" in msg:
                raise Unavailable("bad key")        # ключ неверный — другие модели не помогут
            break                                    # 404/400/5xx — следующая модель
    if limited:
        await _cool_down(int(min(max(wait_max, 15), 90)))
        raise Unavailable("rate limit")
    raise Unavailable("failed")


async def status() -> str:
    """Для /ai — проверка: есть ли ключ, какая модель отвечает, какая ошибка."""
    if not API_KEY:
        return "❌ GEMINI_API_KEY topilmadi. .env ga qo'shing va botni qayta yarating: docker compose up -d --force-recreate bot"
    try:
        await _aclient().delete("ai:cooldown")
    except Exception:
        pass
    try:
        await _generate("Reply with one word: OK", [{"role": "user", "parts": [{"text": "ping"}]}], max_tokens=256)
        last = f"\nOxirgi xato: {LAST_ERROR}" if LAST_ERROR else ""
        return f"✅ AI ishlayapti. Model: {_working}.{last}\nModellar: {', '.join(MODELS)}"
    except Unavailable as e:
        return f"❌ AI ishlamayapti: {e}\n{LAST_ERROR}"


def _audio_part(audio: bytes, mime="audio/ogg"):
    import base64
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(audio).decode()}}


# ─────────────────────────── знания о проекте (команда, партнёры, свои заметки) ───────────────────────────

import time
from pathlib import Path
_KB_CACHE = {"at": 0.0, "text": ""}
EXTRA_FILE = "assistant/extra.txt"      # media/assistant/extra.txt — правится в админке «🤖 AI bilimlari»


def extra_path() -> Path:
    from django.conf import settings
    return Path(settings.MEDIA_ROOT) / EXTRA_FILE


def _project_info_sync() -> str:
    """Публичная информация о проекте из базы. Телефонов и юзернеймов волонтёров здесь нет — только команда."""
    from app_telegram.models import TGUser, TeamMemberYashilQullar, Partner, EcoProject, ProjectParticipation
    from tgbot.i18n import region_label, role_label
    lines = ["Yashil Qo'llar — eco-volunteering youth project in Uzbekistan: tree planting, plogging, clean-ups, eco events. "
             "Goal: grow ecological culture among young people. Website yashilqollar.uz, Telegram bot @yashilqollarbot.",
             f"Numbers now: {TGUser.objects.count()} registered volunteers, {EcoProject.objects.count()} events held/planned, "
             f"{ProjectParticipation.objects.filter(status='attended').count()} confirmed check-ins.",
             "The Telegram bot, the Mini App «Ilova» and the certificate system were developed by Salokhiddin Usmonov (Usmonov Salohiddin).",
             "Certificates are signed by the founder of Yashil Qo'llar — Abdulboriy Akbarov."]
    site_team = list(TeamMemberYashilQullar.objects.all()[:60])
    if site_team:
        lines.append("\nTEAM (from the website):")
        for m in site_team:
            bio = " ".join((m.bio or "").split())[:220]
            tg = f", Telegram @{m.telegram_username.lstrip('@')}" if m.telegram_username else ""
            lines.append(f"- {m.fullname} — {m.get_focus_display()}{tg}{'. ' + bio if bio else ''}")
    staff = list(TGUser.objects.exclude(role=TGUser.Role.VOLUNTEER).order_by('role', 'region', 'fullname')[:250])
    if staff:
        lines.append("\nTEAM IN THE BOT (role, region):")
        for u in staff:
            lines.append(f"- {u.fullname} — {role_label(u.role, 'en')}" + (f", {region_label(u.region, 'en')}" if u.region else ""))
    partners = list(Partner.objects.filter(is_active=True)[:30])
    if partners:
        lines.append("\nPARTNERS / SPONSORS:")
        for pr in partners:
            lines.append(f"- {pr.name}" + (f": {' '.join((pr.description or '').split())[:150]}" if pr.description else ""))
    try:
        extra = extra_path().read_text(encoding="utf-8").strip()
        if extra:
            lines.append("\nEXTRA NOTES FROM THE ADMINS (trust these):\n" + extra[:6000])
    except OSError:
        pass
    return "\n".join(lines)


async def knowledge() -> str:
    """Справочник для ИИ: FAQ + информация о проекте (кэш 10 минут)."""
    if time.time() - _KB_CACHE["at"] > 600 or not _KB_CACHE["text"]:
        from asgiref.sync import sync_to_async
        try:
            info = await sync_to_async(_project_info_sync)()
        except Exception:
            log.exception("project info")
            info = ""
        _KB_CACHE.update(at=time.time(), text=faq.knowledge_text() + "\n\n## PROJECT INFO\n" + info)
    return _KB_CACHE["text"]


def reset_knowledge_cache():
    _KB_CACHE["at"] = 0.0


# ─────────────────────────── помощник для волонтёров ───────────────────────────

_SYSTEM = """You are the help assistant of «Yashil Qo'llar» — an eco-volunteering project in Uzbekistan (Telegram bot @yashilqollarbot, website yashilqollar.uz, Mini App «Ilova» inside the bot).

Rules:
- Answer about using the bot, the website, the Mini App, events, registration, QR codes, points, certificates, and about the project itself: its team, founders, coordinators, partners, history (PROJECT INFO). Use ONLY the HANDBOOK, PROJECT INFO and USER DATA below. Never invent events, dates, places, people, links or features.
- People: you may tell who someone is if they are in PROJECT INFO (name, role, region, public bio). Names may be spelled differently (Salohiddin / Salokhiddin / Salahuddin, Latin or Cyrillic) — match them sensibly. Never reveal phone numbers or private data. For a person not in PROJECT INFO say you have no public information about them.
- If the question isn't covered, or it's off-topic, say briefly that you don't know and advise writing to the region's coordinators (app → Top/Reyting → «Jamoa»).
- You can only explain. You cannot register people, give points, change data or check anyone in — say so if asked.
- Reply in {lang}. Be short and friendly: at most 6 short lines. Use the exact button names from the handbook. Formatting: Telegram HTML only (<b>bold</b>), no Markdown, no tables.

HANDBOOK:
{kb}

USER DATA (read-only, about the person asking):
{user}"""


async def ask(question: str, lang: str, user_ctx: str, history: list | None = None, audio: bytes | None = None) -> str:
    system = _SYSTEM.format(lang=LANG_NAMES.get(lang, "Uzbek"), kb=await knowledge(), user=user_ctx or "—")
    contents = []
    for q, a in (history or [])[-3:]:
        contents += [{"role": "user", "parts": [{"text": q}]}, {"role": "model", "parts": [{"text": a}]}]
    if audio:
        parts = [_audio_part(audio), {"text": VOICE_NOTE}]
    else:
        parts = [{"text": question[:1000]}]
    contents.append({"role": "user", "parts": parts})
    text = await _generate(system, contents, max_tokens=2048)
    return _safe_html(text)


VOICE_NOTE = ("This is a Telegram voice message (most likely Uzbek, maybe Russian or mixed). Listen carefully. "
              "Start your reply with one line: 🎙 «<what the person said, briefly, in their own language>» — then answer the question.")


def _safe_html(text: str) -> str:
    """Оставляем только <b>, <i> — остальное экранируем, чтобы Telegram не отверг сообщение."""
    import html, re
    keep = {}
    def stash(m):
        k = f"\x00{len(keep)}\x00"; keep[k] = m.group(0); return k
    t = re.sub(r"</?(b|i)>", stash, text.replace("**", ""))
    t = html.escape(t, quote=False)
    for k, v in keep.items():
        t = t.replace(k, v)
    return t[:3500]


# ─────────────────────────── команды админа ───────────────────────────

_CMD_SYSTEM = """Convert an admin's command for the Yashil Qo'llar Telegram bot into JSON. The command may be in Uzbek (Latin or Cyrillic), Russian or English, possibly dictated by voice with typos.
Return ONLY a JSON object: {{"transcript": ..., "action": ..., "period": ..., "region": ..., "query": ...}}
transcript — the command as understood (in its original language; for voice — what was said).
action — one of:
  "report"  — list/Excel of people who ATTENDED events (кто пришёл, kelganlar, ro'yxat, excel);
  "stats"   — numbers: new users, attendance, events (статистика, nechta, сколько);
  "coordinators" — who are coordinators/team in a region;
  "events"  — upcoming events list;
  "find"    — find a person (query = name, @username or phone);
  "question" — a general question about the bot/project (how to register, certificates, etc.);
  "unknown" — anything else (including requests to change data, send messages, give roles).
period — one of "today","yesterday","week","month","all" (default "today" for report/stats).
region — one of {regions} or "all" (Tashkent city/region → "tashkent"; default "all").
query — only for "find", else "".
answer — ONLY when action is "question" or "unknown": a short helpful answer (max 6 lines, Telegram HTML <b> only) in {lang}, using ONLY this handbook and PROJECT INFO (team, founders, partners, numbers); never reveal phone numbers. If not covered, say so briefly. Otherwise "".

HANDBOOK:
{kb}
"""


async def parse_command(text: str, regions: list[str], audio: bytes | None = None, lang: str = "uz") -> dict:
    parts = [_audio_part(audio), {"text": "Voice command (probably Uzbek or Russian)."}] if audio else [{"text": text[:500]}]
    raw = await _generate(_CMD_SYSTEM.format(regions=", ".join(regions), lang=LANG_NAMES.get(lang, "Uzbek"), kb=await knowledge()),
                          [{"role": "user", "parts": parts}], json_mode=True, max_tokens=2048)
    try:
        return json.loads(raw)
    except ValueError:
        raise Unavailable("bad json")
