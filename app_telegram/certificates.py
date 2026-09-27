"""
Сертификаты участникам — рисуются на лету из шаблона Canva.

Шаблон: PNG без имени (по умолчанию cert_assets/template.png; загруженный в
админке «🎓 Sertifikat shabloni» лежит в media/certificates/template.png и
важнее). Координаты имени/даты/номера — в media/certificates/layout.json
(правятся там же, с предпросмотром). Поменяли дизайн в Canva — загрузили новый
PNG в админке, код не трогаем. Старые сертификаты тоже сразу в новом дизайне:
файл не хранится, а собирается при открытии (имя — всегда актуальное из профиля).

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
}


def layout() -> dict:
    lay = dict(DEFAULT_LAYOUT)
    try:
        lay.update(json.loads((CUSTOM / "layout.json").read_text()))
    except (OSError, ValueError):
        pass
    return lay


def save_layout(data: dict):
    CUSTOM.mkdir(parents=True, exist_ok=True)
    clean = {k: type(DEFAULT_LAYOUT[k])(v) for k, v in data.items() if k in DEFAULT_LAYOUT}
    (CUSTOM / "layout.json").write_text(json.dumps(clean, ensure_ascii=False, indent=1))


def reset():
    for f in ("layout.json", "template.png"):
        try:
            (CUSTOM / f).unlink()
        except OSError:
            pass


def template_path() -> Path:
    p = CUSTOM / "template.png"
    return p if p.exists() else ASSETS / "template.png"


def save_template(fileobj):
    CUSTOM.mkdir(parents=True, exist_ok=True)
    img = Image.open(fileobj).convert("RGB")
    img.save(CUSTOM / "template.png", "PNG")
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
        f.set_variation_by_axes([600 if kind == "date" else 500])
    return f


def display_name(fullname: str) -> str:
    """«aziza rahimova» / «AZIZA RAHIMOVA» → «Aziza Rahimova»; смешанный регистр оставляем как ввёл человек."""
    n = " ".join((fullname or "").split())
    if n and (n == n.lower() or n == n.upper()):
        n = " ".join(w[:1].upper() + w[1:].lower() for w in n.split())
    return n or "—"


def render(name: str, date_text: str, number: str, lay: dict | None = None) -> Image.Image:
    lay = lay or layout()
    tp = template_path()
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
    if lay.get("show_number") and number:
        d.text((lay["number_x"], lay["number_y"]), f"№ {number}", font=_font("number", int(lay["number_size"])),
               fill=lay["number_color"], anchor="ls")
    return img


def number_of(pp) -> str:
    return f"YQ-{pp.id:06d}"


def render_for(pp) -> Image.Image:
    date = timezone.localtime(pp.project.date).strftime("%d.%m.%Y") if pp.project.date else ""
    return render(display_name(pp.user.fullname), date, number_of(pp))


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


def url(pid: int, ext="pdf") -> str:
    return f"{PUBLIC_URL}/c/{pid}-{sign(pid)}.{ext}"


def attended(pid: int):
    from .models import ProjectParticipation
    return ProjectParticipation.objects.select_related('user', 'project').filter(pk=pid, status='attended').first()
