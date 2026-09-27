"""
🎁 Yashil Qo'llar Wrapped — итоги года каждого волонтёра (как Spotify Wrapped).

stats(user, year)  — цифры: мероприятия, мой вклад (кг/мешки/деревья — impact.share_of),
                      лучшая серия месяцев, любимый сезон, место в регионе, итог всего проекта.
render(...)        — сторис 1080×1920 (JPEG) для Instagram/Telegram.
Ссылка на картинку: /c/w/<id>-<год>-<подпись>.jpg?l=<язык> (подпись HMAC, как у сертификатов).

Когда доступно: с WRAPPED_FROM (по умолчанию 1 декабря) до конца января — за уходящий год.
Админы/основатели видят превью в любое время. В WRAPPED_DAY (по умолчанию 20.12) бот сам
рассылает картинку всем, кто в этом году был хотя бы на одном мероприятии (tgbot/services/wrapped.py).
"""
import hashlib
import hmac
import math
import os
from datetime import date
from functools import lru_cache
from io import BytesIO

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import impact
from .certificates import ASSETS, PUBLIC_URL, SEASONS, SEASON_NAMES, display_name

W, H = 1080, 1920
FROM = os.environ.get("WRAPPED_FROM", "12-01")      # ММ-ДД — с какого дня года доступно


def year_for(today: date | None = None, preview: bool = False) -> int | None:
    """За какой год показывать итоги сегодня (None — ещё рано). preview — админам всегда (текущий год)."""
    d = today or timezone.localdate()
    fm, fd = (int(x) for x in FROM.split("-"))
    if (d.month, d.day) >= (fm, fd):
        return d.year
    if d.month == 1:
        return d.year - 1
    return d.year if preview else None


def can_preview(user) -> bool:
    return bool(user) and (user.is_admin or user.role == "Founder")


# ─────────── цифры ───────────

def _best_streak(months: list[int]) -> int:
    best = cur = 0
    prev = None
    for m in sorted(set(months)):
        cur = cur + 1 if prev is not None and m == prev + 1 else 1
        best, prev = max(best, cur), m
    return best


def community(year: int) -> dict:
    from .models import EcoProject, ProjectParticipation
    key = f"wrapped:community:{year}"
    data = cache.get(key)
    if data is None:
        pps = ProjectParticipation.objects.filter(status='attended', project__date__year=year)
        pids = list(EcoProject.objects.filter(date__year=year, date__lte=timezone.now()).values_list('id', flat=True))
        res = impact.many(pids)
        data = {
            "volunteers": pps.values('user').distinct().count(),
            "checkins": pps.count(),
            "events": len(pids),
            "kg": round(sum(v["kg"] for v in res.values()), 1),
            "trees": int(sum(v["trees"] for v in res.values())),
        }
        cache.set(key, data, 1800)
    return data


def stats(user, year: int) -> dict:
    from . import services
    from .models import ProjectParticipation
    pps = list(ProjectParticipation.objects.filter(user=user, status='attended', project__date__year=year)
               .select_related('project').order_by('project__date'))
    months = [timezone.localtime(pp.project.date).month for pp in pps]
    seasons = {}
    for m in months:
        sl = next(s for s, meta in SEASONS.items() if m in meta["months"])
        seasons[sl] = seasons.get(sl, 0) + 1
    fav = max(seasons, key=lambda s: (seasons[s], -list(SEASONS).index(s))) if seasons else None

    # место среди волонтёров своего региона (Ташкент город+область — вместе) по числу мероприятий за год
    place = top_pct = total = None
    group = services.region_group(user.region)
    if pps and group:
        counts = list(ProjectParticipation.objects.filter(status='attended', project__date__year=year, user__region__in=group)
                      .values('user').annotate(n=Count('id')).values_list('n', flat=True))
        total = len(counts)
        place = sum(1 for c in counts if c > len(pps)) + 1
        top_pct = max(1, math.ceil(place * 100 / total)) if total else None

    first = pps[0].project if pps else None
    return {
        "year": year,
        "name": display_name(user.fullname),
        "events": len(pps),
        "titles": [pp.project.title for pp in pps][-6:],
        "first": {"title": first.title, "date": timezone.localtime(first.date).date().isoformat()} if first else None,
        "months": sorted(set(months)),
        "streak": _best_streak(months),
        "season": fav,
        "share": impact.share_of(user, year),
        "region": user.region,
        "place": place, "top_pct": top_pct, "region_total": total,
        "community": community(year),
    }


# ─────────── ссылка ───────────

def sign(uid: int, year: int) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"wrapped:{uid}:{year}".encode(), hashlib.sha256).hexdigest()[:16]


def verify(uid: int, year: int, sig: str) -> bool:
    return hmac.compare_digest(sign(uid, year), sig or "")


def url(uid: int, year: int, lang: str = "uz") -> str:
    return f"{PUBLIC_URL}/c/w/{uid}-{year}-{sign(uid, year)}.jpg?l={lang}"


# ─────────── картинка ───────────

BG_TOP, BG_BOT = (9, 38, 27), (20, 83, 50)
LIME, MINT, CREAM = (190, 242, 100), (134, 239, 172), (250, 247, 236)
SEASON_RGB = {"kuz": (249, 146, 60), "qish": (147, 197, 253), "bahor": (249, 168, 212), "yoz": (253, 224, 71)}


@lru_cache(maxsize=48)
def _f(kind: str, size: int):
    if kind == "serif":
        f = ImageFont.truetype(str(ASSETS / "fonts" / "PlayfairDisplay-Italic.ttf"), size)
        f.set_variation_by_axes([600])
    else:
        f = ImageFont.truetype(str(ASSETS / "fonts" / "Montserrat.ttf"), size)
        f.set_variation_by_axes([{"black": 900, "bold": 700, "semi": 600, "reg": 500}[kind]])
    return f


@lru_cache(maxsize=1)
def _background() -> Image.Image:
    """Тёмно-зелёный градиент + мягкие светящиеся пятна (один раз на процесс)."""
    strip = Image.new("RGB", (1, 256))
    for y in range(256):
        strip.putpixel((0, y), tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * y / 255) for i in range(3)))
    img = strip.resize((W, H), Image.BILINEAR)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((620, -260, 1380, 500), fill=(*LIME, 70))
    g.ellipse((-360, 1180, 480, 2020), fill=(*MINT, 55))
    g.ellipse((700, 1350, 1250, 1900), fill=(45, 212, 191, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    # листья-контуры по краям
    leaf = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(leaf)
    for cx, cy, s, a in ((960, 300, 150, 40), (90, 1500, 120, -30), (1000, 1720, 90, 60), (120, 360, 70, 15)):
        _leaf(d, cx, cy, s, a, (*LIME, 38))
    return Image.alpha_composite(img, leaf).convert("RGB")


def _leaf(d, cx, cy, s, ang, color):
    pts = []
    for i in range(41):
        tt = i / 40 * math.pi
        x, y = math.sin(tt) * s * 0.42, -math.cos(tt) * s
        pts.append((x, y))
    pts += [(-x, y) for x, y in reversed(pts)]
    r = math.radians(ang)
    rot = [(cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r)) for x, y in pts]
    d.line(rot + [rot[0]], fill=color, width=5)
    d.line([(cx - s * math.sin(-r), cy - s * math.cos(-r)), (cx + s * math.sin(-r), cy + s * math.cos(-r))], fill=color, width=3)


def _center(d, y, text, font, fill):
    d.text((W // 2, y), text, font=font, fill=fill, anchor="ma")


def _fit(d, text, kind, size, max_w):
    while size > 20 and d.textlength(text, font=_f(kind, size)) > max_w:
        size -= 2
    return _f(kind, size)


def _num(v) -> str:
    if isinstance(v, float):
        v = round(v, 1) if v < 10 else round(v)
    s = f"{v:,}".replace(",", " ") if isinstance(v, int) else f"{v:g}"
    return s


def tiles(s: dict, lang: str) -> list:
    """Плитки 2×2: самое интересное из того, что не ноль."""
    from tgbot.i18n import t, region_label
    sh = s["share"]
    cand = []
    if sh["kg"]:
        cand.append(("≈" + _num(sh["kg"]), t("wr_kg", lang)))
    if sh["trees"]:
        cand.append(("≈" + _num(sh["trees"]), t("wr_trees", lang)))
    if s["top_pct"] and s["region_total"] and s["region_total"] >= 5:
        cand.append((f"TOP {s['top_pct']}%", region_label(s["region"], lang) if s["region"] else ""))
    if s["streak"] >= 2:
        cand.append((str(s["streak"]), t("wr_streak", lang)))
    if sh["bags"]:
        cand.append(("≈" + _num(sh["bags"]), t("wr_bags", lang)))
    if len(s["months"]) >= 2:
        cand.append((str(len(s["months"])), t("wr_months", lang)))
    return cand[:4]


def community_tiles(s: dict, lang: str) -> list:
    from tgbot.i18n import t
    c = s["community"]
    cand = [(_num(c["events"]), t("wr_c_events", lang, n="").strip()), (_num(c["checkins"]), t("wr_checkins", lang))]
    if c["kg"]:
        cand.insert(0, (_num(c["kg"]), t("wr_c_kg", lang, n="").strip()))
    if c["trees"]:
        cand.insert(1, (_num(c["trees"]), t("imp_u_trees", lang, n="").strip()))
    return cand[:4]


def render(s: dict, lang: str = "uz") -> Image.Image:
    from tgbot.i18n import t
    img = _background().copy()
    d = ImageDraw.Draw(img, "RGBA")

    _center(d, 120, "YASHIL QO'LLAR", _f("black", 34), LIME)
    d.line((W // 2 - 60, 176, W // 2 + 60, 176), fill=(*LIME, 160), width=3)
    _center(d, 205, t("wr_title", lang).upper(), _f("bold", 30), (*CREAM, 210))
    _center(d, 250, str(s["year"]), _f("black", 250), LIME)
    name = s["name"]
    _center(d, 530, name, _fit(d, name, "serif", 76, 900), CREAM)

    # главная цифра
    if s["events"]:
        hero, hero_lbl = str(s["events"]), t("wr_events", lang)
    else:
        hero, hero_lbl = _num(s["community"]["volunteers"]), t("wr_vol_together", lang)
    d.rounded_rectangle((90, 650, W - 90, 980), radius=48, fill=(255, 255, 255, 22), outline=(*LIME, 90), width=2)
    _center(d, 668, hero, _f("black", 200), CREAM)
    _center(d, 900, hero_lbl, _fit(d, hero_lbl, "semi", 40, 800), (*CREAM, 220))

    # плитки 2×2
    tl = tiles(s, lang) if s["events"] else community_tiles(s, lang)
    y = 1015
    if tl:
        tw, th, gap, x0, y0 = 435, 230, 30, 90, 1015
        for i, (val, lbl) in enumerate(tl):
            x, y = x0 + (i % 2) * (tw + gap), y0 + (i // 2) * (th + gap)
            if i == len(tl) - 1 and i % 2 == 0:
                x = (W - tw) // 2           # нечётная последняя — по центру
            d.rounded_rectangle((x, y, x + tw, y + th), radius=36, fill=(255, 255, 255, 18))
            vf = _fit(d, val, "black", 86, tw - 50)
            d.text((x + tw // 2, y + 40), val, font=vf, fill=LIME, anchor="ma")
            lf = _fit(d, lbl, "semi", 30, tw - 40)
            d.text((x + tw // 2, y + 160), lbl, font=lf, fill=(*CREAM, 215), anchor="ma")
        y = y0 + 2 * th + gap + 40 if len(tl) > 2 else y0 + th + 40
    if not s["events"]:
        _center(d, y, t("wr_join_next", lang), _fit(d, t("wr_join_next", lang), "semi", 40, 880), CREAM)
        y += 90

    # любимый сезон
    if s["season"]:
        idx = {"uz": 0, "ru": 1, "en": 2}.get(lang, 0)
        txt = t("wr_season", lang, s=SEASON_NAMES[s["season"]][idx])
        col = SEASON_RGB[s["season"]]
        f = _f("bold", 38)
        wdt = d.textlength(txt, font=f) + 90
        d.rounded_rectangle(((W - wdt) / 2, y, (W + wdt) / 2, y + 76), radius=38, fill=(*col, 235))
        d.text((W // 2, y + 38), txt, font=f, fill=(20, 40, 28), anchor="mm")
        y += 120

    # вместе
    c = s["community"]
    parts = [t("wr_c_vol", lang, n=_num(c["volunteers"])), t("wr_c_events", lang, n=_num(c["events"]))]
    if c["kg"]:
        parts.append(t("wr_c_kg", lang, n=_num(c["kg"])))
    together = t("wr_together", lang, y=s["year"])
    yb = max(y + 10, 1690)
    _center(d, yb, together, _f("semi", 28), (*CREAM, 170))
    line = " · ".join(parts)
    _center(d, yb + 44, line, _fit(d, line, "bold", 34, 940), CREAM)
    _center(d, 1850, "@yashilqollarbot", _f("bold", 30), LIME)
    return img


def to_jpg(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, "JPEG", quality=90, optimize=True)
    return buf.getvalue()


def image_for(user, year: int, lang: str) -> bytes:
    return to_jpg(render(stats(user, year), lang))
