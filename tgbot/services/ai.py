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
# Запасная модель — Gemma через тот же бесплатный ключ: только текст, без system_instruction и JSON-режима,
# зато обычно намного больший дневной лимит. Отключить: AI_GEMMA=0.
GEMMA = os.environ.get("GEMMA_MODEL", "gemma-3-27b-it").strip()
GEMMA_ON = os.environ.get("AI_GEMMA", "1") != "0" and bool(GEMMA)
DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "15"))
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
LANG_NAMES = {"uz": "Uzbek (Latin script)", "ru": "Russian", "en": "English"}


def enabled() -> bool:
    return bool(API_KEY)


class Unavailable(Exception):
    """ИИ сейчас недоступен (нет ключа, лимит Google, сеть) — отвечаем запасным текстом."""


async def _cooling() -> bool:
    """Все модели на лимите?"""
    for m in MODELS + ([GEMMA] if GEMMA_ON else []):
        if not await _dead_ttl(m):
            return False
    return True


async def _cool_down(seconds=120):  # оставлено для совместимости
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


def _until_daily_reset() -> int:
    """Дневные лимиты Google сбрасываются в полночь по тихоокеанскому времени (~08:00 UTC)."""
    from datetime import datetime, timedelta, timezone as tz
    now = datetime.now(tz.utc)
    reset = now.replace(hour=8, minute=5, second=0, microsecond=0)
    if reset <= now:
        reset += timedelta(days=1)
    return int((reset - now).total_seconds())


async def _dead_ttl(model: str) -> int:
    try:
        return max(0, await _aclient().ttl(f"ai:dead:{model}"))
    except Exception:
        return 0


async def _mark_dead(model: str, seconds: int):
    try:
        await _aclient().set(f"ai:dead:{model}", 1, ex=max(5, int(seconds)))
    except Exception:
        pass


async def _on_429(model: str, data, msg: str) -> float:
    """Лимит: дневной — модель «отдыхает» до сброса; минутный — на столько, сколько просит Google."""
    daily = "perday" in msg.replace(" ", "").lower() or "per day" in msg.lower() or "PerDay" in str(data)
    delay = _retry_delay(data)
    await _mark_dead(model, _until_daily_reset() if daily else max(delay, 20))
    return delay


async def _generate(system: str, contents: list, json_mode=False, max_tokens=4096, gemma_contents: list | None = None) -> str:
    """
    Запрос к ИИ. Модели Gemini по очереди (у каждой СВОЙ бесплатный лимит); модели на лимите
    пропускаем, пока не «отдохнут». Все Gemini исчерпаны — запасная Gemma (если передан
    gemma_contents: только текст, компактный справочник). Пустой ответ — ещё раз с запасом.
    Ничего не вышло из-за лимитов — Unavailable("rate limit") → «ИИ занят».
    """
    global _working, LAST_ERROR
    if not API_KEY:
        LAST_ERROR = "GEMINI_API_KEY yo'q (.env)"
        raise Unavailable("no key")
    order = ([_working] if _working and _working != GEMMA else []) + [m for m in MODELS if m != _working]
    limited = False
    for model in order:
        if await _dead_ttl(model):
            limited = True
            continue
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
                tokens = min(tokens * 2, 8192)
                continue
            if status == 400 and "thinking" in msg.lower() and thinking_off:
                thinking_off = False
                continue
            LAST_ERROR = f"{model}: HTTP {status} {msg[:200]}"
            log.warning("gemini %s", LAST_ERROR)
            if status == 429:
                delay = await _on_429(model, data, msg)
                if attempt == 0 and delay <= 12 and "perday" not in msg.replace(" ", "").lower():
                    await asyncio.sleep(delay + 0.5)
                    continue
                limited = True
                break
            if status in (400, 403) and "API key" in msg:
                raise Unavailable("bad key")
            break
    # ── запасная Gemma: только текст ──
    if GEMMA_ON and gemma_contents is not None and not await _dead_ttl(GEMMA):
        cfg = {"temperature": 0.3, "maxOutputTokens": min(max_tokens, 2048)}
        try:
            status, data = await _post(GEMMA, {"contents": gemma_contents, "generationConfig": cfg})
        except (aiohttp.ClientError, TimeoutError) as e:
            LAST_ERROR = f"network: {e}"
            raise Unavailable(str(e))
        if status == 200:
            text, finish = _extract(data)
            if text:
                return text
            LAST_ERROR = f"{GEMMA}: empty answer ({finish})"
        else:
            msg = (data or {}).get("error", {}).get("message", "") if isinstance(data, dict) else str(data)
            LAST_ERROR = f"{GEMMA}: HTTP {status} {msg[:200]}"
            log.warning("gemma %s", LAST_ERROR)
            if status == 429:
                await _on_429(GEMMA, data, msg)
                limited = True
    if limited:
        raise Unavailable("rate limit")
    raise Unavailable("failed")


def _gemma_contents(system: str, history: list, text: str) -> list:
    """У Gemma нет system_instruction — инструкцию кладём в начало первого сообщения пользователя."""
    contents = []
    for q, a in (history or [])[-2:]:
        contents += [{"role": "user", "parts": [{"text": q}]}, {"role": "model", "parts": [{"text": a}]}]
    contents.append({"role": "user", "parts": [{"text": text}]})
    contents[0]["parts"][0]["text"] = f"{system}\n\n---\n{contents[0]['parts'][0]['text']}"
    return contents


async def models_state() -> str:
    lines = []
    for m in MODELS + ([GEMMA + " (zaxira, faqat matn)"] if GEMMA_ON else []):
        name = m.split(" ")[0]
        ttl = await _dead_ttl(name)
        mark = "✅" if not ttl else f"⏳ limit, {ttl // 3600} soat {ttl % 3600 // 60} daq qoldi" if ttl > 3600 else f"⏳ limit, {ttl} soniya"
        lines.append(f"• {m}: {mark}" + (" ← hozir shu" if name == _working else ""))
    return "\n".join(lines)


async def status() -> str:
    """Для /ai — проверка: есть ли ключ, какая модель отвечает, какая ошибка, какие модели на лимите."""
    if not API_KEY:
        return "❌ GEMINI_API_KEY topilmadi. .env ga qo'shing va botni qayta yarating: docker compose up -d --force-recreate bot"
    try:
        await _generate("Reply with one word: OK", [{"role": "user", "parts": [{"text": "ping"}]}], max_tokens=256,
                        gemma_contents=[{"role": "user", "parts": [{"text": "Reply with one word: OK"}]}])
        last = f"\nOxirgi xato: {LAST_ERROR}" if LAST_ERROR else ""
        return f"✅ AI ishlayapti.{last}\n\n{await models_state()}"
    except Unavailable as e:
        return f"❌ AI ishlamayapti: {e}\n{LAST_ERROR}\n\n{await models_state()}"


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


def _project_info_compact_sync() -> str:
    """Кратко о проекте для запасной модели: без длинных списков (у Gemma маленький лимит токенов в минуту)."""
    from app_telegram.models import TGUser, TeamMemberYashilQullar, Partner
    from tgbot.i18n import region_label, role_label
    lines = ["Yashil Qo'llar — eco-volunteering youth project in Uzbekistan. Website yashilqollar.uz, bot @yashilqollarbot.",
             "The bot, the Mini App «Ilova» and certificates were developed by Salokhiddin Usmonov (Usmonov Salohiddin).",
             "Certificates are signed by the founder of Yashil Qo'llar — Abdulboriy Akbarov."]
    for m in TeamMemberYashilQullar.objects.all()[:15]:
        lines.append(f"- {m.fullname} — {m.get_focus_display()}. {' '.join((m.bio or '').split())[:120]}")
    for u in TGUser.objects.filter(role__in=["Founder", "head_coordinator", "main_coordinator"]).order_by('role')[:20]:
        lines.append(f"- {u.fullname} — {role_label(u.role, 'en')}" + (f", {region_label(u.region, 'en')}" if u.region else ""))
    names = ", ".join(p.name for p in Partner.objects.filter(is_active=True)[:15])
    if names:
        lines.append(f"Partners: {names}.")
    try:
        extra = extra_path().read_text(encoding="utf-8").strip()
        if extra:
            lines.append("Admin notes: " + extra[:1500])
    except OSError:
        pass
    return "\n".join(lines)


_KB_SMALL = {"at": 0.0, "text": ""}


async def knowledge_small(question: str, lang: str) -> str:
    if time.time() - _KB_SMALL["at"] > 600 or not _KB_SMALL["text"]:
        from asgiref.sync import sync_to_async
        try:
            _KB_SMALL.update(at=time.time(), text=await sync_to_async(_project_info_compact_sync)())
        except Exception:
            log.exception("compact info")
    return faq.compact_text(faq.ranked(question, 5), lang) + "\n\n## PROJECT INFO\n" + _KB_SMALL["text"]


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
    _KB_SMALL["at"] = 0.0


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
    gemma = None
    if not audio and GEMMA_ON:
        small = _SYSTEM.format(lang=LANG_NAMES.get(lang, "Uzbek"), kb=await knowledge_small(question, lang), user=user_ctx or "—")
        gemma = _gemma_contents(small, history, question[:1000])
    text = await _generate(system, contents, max_tokens=2048, gemma_contents=gemma)
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
    gemma = None
    if not audio and GEMMA_ON:
        small = _CMD_SYSTEM.format(regions=", ".join(regions), lang=LANG_NAMES.get(lang, "Uzbek"), kb=await knowledge_small(text, lang))
        gemma = _gemma_contents(small + "\nReturn ONLY the JSON object, no other text.", [], text[:500])
    raw = await _generate(_CMD_SYSTEM.format(regions=", ".join(regions), lang=LANG_NAMES.get(lang, "Uzbek"), kb=await knowledge()),
                          [{"role": "user", "parts": parts}], json_mode=True, max_tokens=2048, gemma_contents=gemma)
    import re as _re
    m = _re.search(r"\{.*\}", raw, _re.S)
    try:
        return json.loads(m.group(0) if m else raw)
    except ValueError:
        raise Unavailable("bad json")
