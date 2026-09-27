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
import json
import logging
import os
from datetime import date

import aiohttp

from . import faq
from .lang import _aclient

log = logging.getLogger(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip()
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


async def _generate(system: str, contents: list, json_mode=False, max_tokens=2048) -> str:
    if not API_KEY:
        raise Unavailable("no key")
    if await _cooling():
        raise Unavailable("cooldown")
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.2 if json_mode else 0.4, "maxOutputTokens": max_tokens},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as s:
            async with s.post(URL.format(model=MODEL), json=body, headers={"x-goog-api-key": API_KEY}) as resp:
                if resp.status == 429:
                    await _cool_down()
                    raise Unavailable("rate limit")
                data = await resp.json(content_type=None)
                if resp.status != 200:
                    log.warning("gemini %s: %s", resp.status, str(data)[:300])
                    raise Unavailable(f"http {resp.status}")
    except (aiohttp.ClientError, TimeoutError) as e:
        raise Unavailable(str(e))
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    except (KeyError, IndexError, TypeError):
        raise Unavailable("empty answer")
    if not text:
        raise Unavailable("empty answer")
    return text


# ─────────────────────────── помощник для волонтёров ───────────────────────────

_SYSTEM = """You are the help assistant of «Yashil Qo'llar» — an eco-volunteering project in Uzbekistan (Telegram bot @yashilqollarbot, website yashilqollar.uz, Mini App «Ilova» inside the bot).

Rules:
- Answer ONLY about using the bot, the website, the Mini App, events, registration, QR codes, points, certificates and the project. Use ONLY the HANDBOOK and the USER DATA below. Never invent events, dates, places, people, links or features.
- If the handbook doesn't cover the question, or it's off-topic, say briefly that you don't know and advise writing to the region's coordinators (app → Top/Reyting → «Jamoa»).
- You can only explain. You cannot register people, give points, change data or check anyone in — say so if asked.
- Reply in {lang}. Be short and friendly: at most 6 short lines. Use the exact button names from the handbook. Formatting: Telegram HTML only (<b>bold</b>), no Markdown, no tables.

HANDBOOK:
{kb}

USER DATA (read-only, about the person asking):
{user}"""


async def ask(question: str, lang: str, user_ctx: str, history: list | None = None) -> str:
    system = _SYSTEM.format(lang=LANG_NAMES.get(lang, "Uzbek"), kb=faq.knowledge_text(), user=user_ctx or "—")
    contents = []
    for q, a in (history or [])[-3:]:
        contents += [{"role": "user", "parts": [{"text": q}]}, {"role": "model", "parts": [{"text": a}]}]
    contents.append({"role": "user", "parts": [{"text": question[:1000]}]})
    text = await _generate(system, contents, max_tokens=1500)
    return _safe_html(text)


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
Return ONLY a JSON object: {{"action": ..., "period": ..., "region": ..., "query": ...}}
action — one of:
  "report"  — list/Excel of people who ATTENDED events (кто пришёл, kelganlar, ro'yxat, excel);
  "stats"   — numbers: new users, attendance, events (статистика, nechta, сколько);
  "coordinators" — who are coordinators/team in a region;
  "events"  — upcoming events list;
  "find"    — find a person (query = name, @username or phone);
  "unknown" — anything else (including requests to change data, send messages, give roles).
period — one of "today","yesterday","week","month","all" (default "today" for report/stats).
region — one of {regions} or "all" (Tashkent city/region → "tashkent"; default "all").
query — only for "find", else "".
"""


async def parse_command(text: str, regions: list[str]) -> dict:
    raw = await _generate(_CMD_SYSTEM.format(regions=", ".join(regions)),
                          [{"role": "user", "parts": [{"text": text[:500]}]}], json_mode=True, max_tokens=512)
    try:
        return json.loads(raw)
    except ValueError:
        raise Unavailable("bad json")
