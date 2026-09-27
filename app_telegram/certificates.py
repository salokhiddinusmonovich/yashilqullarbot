"""
Сертификаты участникам — рисуются на лету из шаблона Canva.

Дизайны — библиотека (админка «🎓 Sertifikat dizaynlari»): 🍂 Kuz, ❄️ Qish, 🌸 Bahor,
☀️ Yoz + свои. У каждого свой PNG из Canva (без имени), свои координаты и месяцы.
Дизайн выбирается по дате мероприятия (или дизайн привязан к конкретному мероприятию).
Сезон без своего PNG → стандартный осенний (cert_assets/template.png).
Файл сертификата не хранится — собирается при открытии: имя всегда актуальное,
а летнее мероприятие навсегда остаётся в летнем дизайне.

Кому: только отметки «пришёл» (ProjectParticipation.status='attended').
Ссылка: /c/<id>-<подпись>.pdf|jpg — подпись HMAC от SECRET_KEY, угадать нельзя.
Номер: YQ-<id участия>, не меняется.
"""
import hashlib
import hmac
import json
import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).parent / "cert_assets"
CUSTOM = Path(settings.MEDIA_ROOT) / "certificates"
PUBLIC_URL = (os.environ.get("PUBLIC_API_URL") or "https://api.yashilqollar.uz").rstrip("/")

# координаты — для шаблона 1754×1240 (A4 альбомная, 150 dpi), как дизайн из Canva
DEFAULT_LAYOUT = {
    "name_x": 563, "name_y": 606, "name_max_w": 700, "name_size": 80, "name_color": "#BF5310",
    "date_x": 417, "date_y": 1022, "date_size": 27, "date_color": "#464646",
    "number_x": 72, "number_y": 78, "number_size": 19, "number_color": "#968C7D", "show_number": True,
    # название мероприятия (если в дизайне оставили пустую строку под текст) — по умолчанию выключено
    "event_x": 563, "event_y": 700, "event_max_w": 820, "event_size": 30, "event_color": "#464646", "event_show": False,
    # абзац с названием мероприятия: {event} — название; строка, начинающаяся с «*», — жирная.
    # Шрифт сам уменьшается, чтобы обычный текст уложился в body_lines строк.
    "body_x": 573, "body_y": 690, "body_max_w": 860, "body_size": 25, "body_line": 33, "body_lines": 4,
    "body_color": "#545F5B", "body_show": False, "body_text": "",
    # QR для проверки подлинности (ведёт на /c/v/…) — в пустом левом верхнем углу
    "qr_x": 72, "qr_y": 100, "qr_size": 130, "qr_color": "#3B4A42", "qr_show": True,
}

# Встроенный осенний дизайн: абзац из Canva («...in the Plogging Campaign...») убран с картинки
# (cert_assets/template_body.png) и пишется системой — с названием КАЖДОГО мероприятия.
BUILTIN_TEMPLATE = "template_body.png"
BUILTIN_LAYOUT = {
    "body_show": True,
    "body_text": "for actively participating in «{event}». Your responsibility, physical effort, and positive spirit have contributed "
                 "to making our environment cleaner and greener. We truly appreciate your dedication to protecting nature and "
                 "promoting an eco-friendly lifestyle.\n*Thank you for being part of this meaningful initiative.",
}

# ─────────── библиотека дизайнов ───────────
# media/certificates/designs/<slug>/{template.png, layout.json, meta.json}
# Сезоны выбираются по месяцу мероприятия; свой дизайн можно привязать к конкретным мероприятиям.
# Сезон без загруженного PNG → стандартный дизайн (осенний, из кода).
DESIGNS = CUSTOM / "designs"
SEASONS = {
    "kuz": {"name": "Kuz", "emoji": "🍂", "months": [9, 10, 11]},
    "qish": {"name": "Qish", "emoji": "❄️", "months": [12, 1, 2]},
    "bahor": {"name": "Bahor", "emoji": "🌸", "months": [3, 4, 5]},
    "yoz": {"name": "Yoz", "emoji": "☀️", "months": [6, 7, 8]},
}
FALLBACK = "kuz"


def _migrate_legacy():
    """Раньше был один шаблон (media/certificates/template.png + layout.json) — переносим его в «🍂 Kuz»."""
    d = DESIGNS / FALLBACK
    for f in ("template.png", "layout.json"):
        old = CUSTOM / f
        if old.exists() and not (d / f).exists():
            d.mkdir(parents=True, exist_ok=True)
            old.replace(d / f)


def _dir(slug: str) -> Path:
    return DESIGNS / slug


def meta(slug: str) -> dict:
    base = dict(SEASONS.get(slug, {"name": slug, "emoji": "🎨", "months": []}))
    base.update({"events": [], "season": slug in SEASONS})
    try:
        base.update(json.loads((_dir(slug) / "meta.json").read_text()))
    except (OSError, ValueError):
        pass
    base["slug"] = slug
    return base


def save_meta(slug: str, months=None, events=None, name=None, emoji=None):
    m = meta(slug)
    if months is not None:
        m["months"] = sorted({int(x) for x in months if 1 <= int(x) <= 12})
    if events is not None:
        m["events"] = sorted({int(x) for x in events})
    if name:
        m["name"] = name[:40]
    if emoji:
        m["emoji"] = emoji[:4]
    _dir(slug).mkdir(parents=True, exist_ok=True)
    keep = {k: m[k] for k in ("name", "emoji", "months", "events")}
    (_dir(slug) / "meta.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1))


def has_template(slug: str) -> bool:
    return (_dir(slug) / "template.png").exists()


def designs() -> list:
    """Все дизайны: 4 сезона (всегда) + свои. ready — есть ли свой PNG (у «Kuz» есть и встроенный)."""
    _migrate_legacy()
    slugs = list(SEASONS)
    if DESIGNS.exists():
        slugs += sorted(p.name for p in DESIGNS.iterdir() if p.is_dir() and p.name not in SEASONS)
    out = []
    for sl in slugs:
        m = meta(sl)
        m["ready"] = has_template(sl) or sl == FALLBACK
        m["custom_png"] = has_template(sl)
        out.append(m)
    return out


def create_design(name: str, emoji: str = "🎨") -> str:
    import re as _re
    base = _re.sub(r"[^a-z0-9]+", "-", (name or "dizayn").lower()).strip("-")[:20] or "dizayn"
    slug, n = base, 2
    while _dir(slug).exists() or slug in SEASONS:
        slug, n = f"{base}-{n}", n + 1
    _dir(slug).mkdir(parents=True, exist_ok=True)
    save_meta(slug, months=[], events=[], name=name or slug, emoji=emoji or "🎨")
    return slug


def delete_design(slug: str):
    """Свой дизайн — удаляем; сезон — только его PNG и настройки (вернётся стандартный)."""
    import shutil
    d = _dir(slug)
    if slug in SEASONS:
        for f in ("template.png", "layout.json", "meta.json"):
            try:
                (d / f).unlink()
            except OSError:
                pass
    elif d.exists():
        shutil.rmtree(d, ignore_errors=True)


def design_for(project) -> str:
    """Какой дизайн у мероприятия: привязанный к нему → по месяцу (где есть PNG) → стандартный."""
    ds = designs()
    for d in ds:
        if project.id in d.get("events", []) and d["ready"]:
            return d["slug"]
    month = timezone.localtime(project.date).month if project.date else timezone.localdate().month
    for d in ds:
        if month in d.get("months", []) and d["ready"] and not d.get("events"):
            return d["slug"]
    return FALLBACK


def layout(slug: str | None = None) -> dict:
    _migrate_legacy()
    lay = dict(DEFAULT_LAYOUT)
    if not has_template(slug or FALLBACK):
        lay.update(BUILTIN_LAYOUT)          # встроенный дизайн — абзац пишет система
    try:
        lay.update(json.loads((_dir(slug or FALLBACK) / "layout.json").read_text()))
    except (OSError, ValueError):
        pass
    return lay


def save_layout(data: dict, slug: str = FALLBACK):
    _dir(slug).mkdir(parents=True, exist_ok=True)
    clean = {}
    for k, v in data.items():
        if k in DEFAULT_LAYOUT:
            d = DEFAULT_LAYOUT[k]
            clean[k] = bool(v) if isinstance(d, bool) else type(d)(v)
    (_dir(slug) / "layout.json").write_text(json.dumps(clean, ensure_ascii=False, indent=1))


def reset(slug: str = FALLBACK):
    delete_design(slug)


def template_path(slug: str | None = None) -> Path:
    _migrate_legacy()
    p = _dir(slug or FALLBACK) / "template.png"
    if p.exists():
        return p
    b = ASSETS / BUILTIN_TEMPLATE
    return b if b.exists() else ASSETS / "template.png"


def save_template(fileobj, slug: str = FALLBACK):
    _dir(slug).mkdir(parents=True, exist_ok=True)
    img = Image.open(fileobj).convert("RGB")
    img.save(_dir(slug) / "template.png", "PNG")
    return img.size


@lru_cache(maxsize=4)
def _template(path: str, mtime: float) -> Image.Image:
    return Image.open(path).convert("RGB")


@lru_cache(maxsize=32)
def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    if kind == "name":
        f = ImageFont.truetype(str(ASSETS / "fonts" / "PlayfairDisplay-Italic.ttf"), size)
        f.set_variation_by_axes([700])
    else:
        f = ImageFont.truetype(str(ASSETS / "fonts" / "Montserrat.ttf"), size)
        f.set_variation_by_axes([{"date": 600, "body": 400, "bodyb": 700}.get(kind, 500)])
    return f


def display_name(fullname: str) -> str:
    """«aziza rahimova» / «AZIZA RAHIMOVA» → «Aziza Rahimova»; смешанный регистр оставляем как ввёл человек."""
    n = " ".join((fullname or "").split())
    if n and (n == n.lower() or n == n.upper()):
        n = " ".join(w[:1].upper() + w[1:].lower() for w in n.split())
    return n or "—"


def render(name: str, date_text: str, number: str, lay: dict | None = None, slug: str | None = None, event_title: str = "",
           verify_url: str = "") -> Image.Image:
    lay = lay or layout(slug)
    tp = template_path(slug)
    img = _template(str(tp), tp.stat().st_mtime).copy()
    d = ImageDraw.Draw(img)
    size = int(lay["name_size"])
    font = _font("name", size)
    while font.getlength(name) > lay["name_max_w"] and size > 28:   # длинное имя — уменьшаем, чтобы влезло в линию
        size -= 2
        font = _font("name", size)
    d.text((lay["name_x"], lay["name_y"]), name, font=font, fill=lay["name_color"], anchor="ms")
    if date_text:
        d.text((lay["date_x"], lay["date_y"]), date_text, font=_font("date", int(lay["date_size"])), fill=lay["date_color"], anchor="ms")
    if lay.get("event_show") and event_title:
        text = f"«{event_title}»"
        esize = int(lay["event_size"])
        ef = _font("date", esize)
        while ef.getlength(text) > lay["event_max_w"] and esize > 14:
            esize -= 1
            ef = _font("date", esize)
        d.text((lay["event_x"], lay["event_y"]), text, font=ef, fill=lay["event_color"], anchor="ms")
    if lay.get("body_show") and lay.get("body_text"):
        _draw_body(d, lay, event_title or "Yashil Qo'llar")
    if lay.get("qr_show"):
        _draw_qr(img, d, lay, verify_url or f"{PUBLIC_URL}/c/v/")
    if lay.get("show_number") and number:
        d.text((lay["number_x"], lay["number_y"]), f"№ {number}", font=_font("number", int(lay["number_size"])),
               fill=lay["number_color"], anchor="ls")
    return img


def _draw_qr(img, d, lay: dict, data: str):
    """Небольшой QR на прозрачном фоне дизайна + подпись «Tekshirish · Verify»."""
    import qrcode
    size = int(lay["qr_size"])
    qr = qrcode.QRCode(border=0, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    # маска: модули QR = 255 (туда кладём цвет), фон = 0 (остаётся сам дизайн, без белого квадрата)
    mask = qr.make_image(fill_color="white", back_color="black").convert("L").resize((size, size), Image.NEAREST)
    ink = Image.new("RGB", (size, size), lay["qr_color"])
    img.paste(ink, (int(lay["qr_x"]), int(lay["qr_y"])), mask)
    d.text((int(lay["qr_x"]) + size / 2, int(lay["qr_y"]) + size + 22), "Tekshirish · Verify",
           font=_font("number", max(12, size // 9)), fill=lay["qr_color"], anchor="ms")


def _wrap(text: str, font, max_w: int) -> list:
    lines, line = [], ""
    for w in text.split():
        test = f"{line} {w}".strip()
        if font.getlength(test) <= max_w or not line:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def _draw_body(d, lay: dict, event_title: str):
    """Абзац по центру: {event} → название мероприятия, «*строка» — жирная. Длинное название — шрифт меньше."""
    paras = [p.strip() for p in str(lay["body_text"]).replace("{event}", event_title).split("\n") if p.strip()]
    size, max_w = int(lay["body_size"]), int(lay["body_max_w"])
    while True:
        reg, bold = _font("body", size), _font("bodyb", size)
        wrapped = [(bool(p.startswith("*")), _wrap(p.lstrip("*").strip(), bold if p.startswith("*") else reg, max_w)) for p in paras]
        normal = sum(len(ls) for b, ls in wrapped if not b)
        if normal <= int(lay["body_lines"]) or size <= 18:
            break
        size -= 1
    step = int(lay["body_line"]) * size / int(lay["body_size"])
    y = lay["body_y"]
    for is_bold, ls in wrapped:
        for ln in ls:
            d.text((lay["body_x"], y), ln, font=bold if is_bold else reg, fill=lay["body_color"], anchor="ms")
            y += step


def number_of(pp) -> str:
    return f"YQ-{pp.id:06d}"


def render_for(pp) -> Image.Image:
    date = timezone.localtime(pp.project.date).strftime("%d.%m.%Y") if pp.project.date else ""
    return render(display_name(pp.user.fullname), date, number_of(pp), slug=design_for(pp.project), event_title=pp.project.title,
                  verify_url=verify_url(pp.id))


def to_pdf(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, "PDF", resolution=150.0, quality=92)
    return buf.getvalue()


def to_jpg(img: Image.Image, max_w: int | None = None, quality=88) -> bytes:
    if max_w and img.width > max_w:
        img = img.resize((max_w, round(img.height * max_w / img.width)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def filename(pp, ext="pdf") -> str:
    import re
    title = re.sub(r"[^\w\-]+", "_", pp.project.title, flags=re.UNICODE).strip("_")[:40] or "tadbir"
    return f"sertifikat_{title}_{number_of(pp)}.{ext}"


# ─────────── подписанные ссылки ───────────

def sign(pid: int) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"cert:{pid}".encode(), hashlib.sha256).hexdigest()[:16]


def verify(pid: int, sig: str) -> bool:
    return hmac.compare_digest(sign(pid), sig or "")


def verify_url(pid: int) -> str:
    """Публичная страница проверки (ссылка в QR на сертификате)."""
    return f"{PUBLIC_URL}/c/v/{pid}-{sign(pid)[:10]}"


def verify_short(pid: int, sig: str) -> bool:
    return hmac.compare_digest(sign(pid)[:10], sig or "")


# ─────────── сезоны: для группировки «🍂 Kuz 2025 / ❄️ Qish 2025–26» ───────────
SEASON_NAMES = {"kuz": ("Kuz", "Осень", "Autumn"), "qish": ("Qish", "Зима", "Winter"),
                "bahor": ("Bahor", "Весна", "Spring"), "yoz": ("Yoz", "Лето", "Summer")}


def season_of(dt, lang: str = "uz") -> tuple:
    """(ключ для сортировки, подпись): зима декабря относится к сезону «2025–26»."""
    d = timezone.localtime(dt)
    m, y = d.month, d.year
    slug = next(sl for sl, meta_ in SEASONS.items() if m in meta_["months"])
    if slug == "qish":
        start = y if m == 12 else y - 1
        year = f"{start}–{str(start + 1)[2:]}"
        order = start * 10 + 4
    else:
        year = str(y)
        order = y * 10 + {"bahor": 1, "yoz": 2, "kuz": 3}[slug]
    idx = {"uz": 0, "ru": 1, "en": 2}.get(lang, 0)
    return order, f"{SEASONS[slug]['emoji']} {SEASON_NAMES[slug][idx]} {year}"


def url(pid: int, ext="pdf") -> str:
    return f"{PUBLIC_URL}/c/{pid}-{sign(pid)}.{ext}"


def attended(pid: int):
    from .models import ProjectParticipation
    return ProjectParticipation.objects.select_related('user', 'project').filter(pk=pid, status='attended').first()
