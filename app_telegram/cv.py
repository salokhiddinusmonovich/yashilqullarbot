"""
📄 «Volontyor CV» — PDF со всеми мероприятиями человека (для вузов, работы, стипендий).

A4 книжная, рисуется Pillow теми же шрифтами, что сертификаты. Только правда из базы:
отметки «пришёл», даты, регионы, номера сертификатов, баллы. Часов в базе нет — не пишем.
Ссылка /c/cv/<id>-<подпись>.pdf (подпись HMAC, как у сертификатов). Язык — язык человека.
"""
import hashlib
import hmac
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw

from . import certificates as C

W, H = 1240, 1754           # A4 при 150 dpi
M = 90                      # поля
GREEN, DARK, MUTED, LINE, CREAM = (21, 128, 61), (22, 36, 28), (110, 110, 100), (225, 220, 205), (250, 246, 236)

TXT = {
    "title": {"uz": "VOLONTYORLIK FAOLIYATI", "ru": "ВОЛОНТЁРСКАЯ ДЕЯТЕЛЬНОСТЬ", "en": "VOLUNTEER RECORD"},
    "sub": {"uz": "Yashil Qo'llar ekologik volontyorlik loyihasi ma'lumotnomasi", "ru": "Справка экологического волонтёрского проекта Yashil Qo'llar",
            "en": "Statement of the Yashil Qo'llar eco-volunteering project"},
    "region": {"uz": "Hudud", "ru": "Регион", "en": "Region"},
    "since": {"uz": "Qo'shilgan", "ru": "С нами с", "en": "Joined"},
    "events": {"uz": "Tadbirlar", "ru": "Мероприятий", "en": "Events"},
    "points": {"uz": "Eko-ball", "ru": "Эко-баллов", "en": "Eco points"},
    "first": {"uz": "Birinchi tadbir", "ru": "Первое мероприятие", "en": "First event"},
    "last": {"uz": "Oxirgi tadbir", "ru": "Последнее мероприятие", "en": "Latest event"},
    "table": {"uz": "Qatnashgan tadbirlari", "ru": "Посещённые мероприятия", "en": "Events attended"},
    "h_no": {"uz": "№", "ru": "№", "en": "#"}, "h_date": {"uz": "Sana", "ru": "Дата", "en": "Date"},
    "h_event": {"uz": "Tadbir", "ru": "Мероприятие", "en": "Event"}, "h_region": {"uz": "Hudud", "ru": "Регион", "en": "Region"},
    "h_cert": {"uz": "Sertifikat", "ru": "Сертификат", "en": "Certificate"},
    "none": {"uz": "Hozircha tasdiqlangan qatnashuv yo'q.", "ru": "Подтверждённых участий пока нет.", "en": "No confirmed participation yet."},
    "foot": {"uz": "Faqat QR-kod orqali tasdiqlangan qatnashuvlar ko'rsatilgan. Hujjat {date} da yaratildi.",
             "ru": "Указаны только участия, подтверждённые по QR-коду. Документ создан {date}.",
             "en": "Only participation confirmed by QR code is listed. Generated on {date}."},
    "page": {"uz": "bet", "ru": "стр.", "en": "page"},
}


def _t(key, lang):
    return TXT[key].get(lang) or TXT[key]["uz"]


def sign(uid: int) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"cv:{uid}".encode(), hashlib.sha256).hexdigest()[:16]


def verify(uid: int, sig: str) -> bool:
    return hmac.compare_digest(sign(uid), sig or "")


def url(uid: int) -> str:
    return f"{C.PUBLIC_URL}/c/cv/{uid}-{sign(uid)}.pdf"


def _fit(d, text, font_kind, size, max_w):
    f = C._font(font_kind, size)
    while f.getlength(text) > max_w and size > 12:
        size -= 1
        f = C._font(font_kind, size)
    return f


def _ellipsis(d, text, font, max_w):
    if font.getlength(text) <= max_w:
        return text
    while text and font.getlength(text + "…") > max_w:
        text = text[:-1]
    return text + "…"


def build(user, lang: str = "uz") -> bytes:
    from tgbot.i18n import region_label, role_label
    from .models import ProjectParticipation
    parts = list(ProjectParticipation.objects.filter(user=user, status='attended').select_related('project').order_by('project__date'))
    logo = Image.open(C.ASSETS / "logo.jpg").convert("RGB").resize((120, 120))
    today = timezone.localdate().strftime("%d.%m.%Y")
    pages, rows_per_first, rows_per_next = [], 16, 30
    chunks = [parts[:rows_per_first]] + [parts[i:i + rows_per_next] for i in range(rows_per_first, len(parts), rows_per_next)]
    total_pages = len(chunks)
    n = 0
    for pi, chunk in enumerate(chunks):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        y = M
        if pi == 0:
            d.rectangle((0, 0, W, 250), fill=CREAM)
            d.rectangle((0, 250, W, 256), fill=GREEN)
            img.paste(logo, (M, 64))
            d.text((M + 150, 100), "YASHIL QO'LLAR", font=C._font("date", 40), fill=GREEN)
            d.text((M + 150, 150), _t("sub", lang), font=C._font("number", 22), fill=MUTED)
            y = 300
            d.text((M, y), _t("title", lang), font=C._font("date", 24), fill=GREEN)
            y += 40
            name = C.display_name(user.fullname)
            d.text((M, y + 60), name, font=_fit(d, name, "name", 64, W - 2 * M), fill=DARK, anchor="ls")
            y += 90
            since = timezone.localtime(user.created).strftime("%m.%Y") if getattr(user, "created", None) else "—"
            meta = f"{_t('region', lang)}: {region_label(user.region, lang) if user.region else '—'}   ·   {role_label(user.role, lang)}   ·   {_t('since', lang)}: {since}"
            d.text((M, y), meta, font=C._font("number", 24), fill=MUTED)
            y += 60
            stats = [(str(len(parts)), _t("events", lang)), (str(user.balance), _t("points", lang)),
                     (timezone.localtime(parts[0].project.date).strftime("%d.%m.%Y") if parts else "—", _t("first", lang)),
                     (timezone.localtime(parts[-1].project.date).strftime("%d.%m.%Y") if parts else "—", _t("last", lang))]
            bw = (W - 2 * M - 3 * 20) // 4
            for i, (big, small) in enumerate(stats):
                x = M + i * (bw + 20)
                d.rounded_rectangle((x, y, x + bw, y + 130), radius=18, fill=CREAM, outline=LINE, width=2)
                d.text((x + 22, y + 70), big, font=_fit(d, big, "date", 44, bw - 40), fill=GREEN, anchor="ls")
                d.text((x + 22, y + 105), small, font=C._font("number", 20), fill=MUTED)
            y += 180
            d.text((M, y), _t("table", lang).upper(), font=C._font("date", 22), fill=DARK)
            y += 44
        cols = [(M, _t("h_no", lang), 60), (M + 60, _t("h_date", lang), 160), (M + 220, _t("h_event", lang), 430),
                (M + 650, _t("h_region", lang), 210), (M + 860, _t("h_cert", lang), W - 2 * M - 860)]
        d.rectangle((M, y, W - M, y + 44), fill=GREEN)
        for x, title, _w in cols:
            d.text((x + 12, y + 30), title, font=C._font("date", 19), fill="white", anchor="ls")
        y += 44
        if not parts:
            d.text((M + 12, y + 50), _t("none", lang), font=C._font("number", 22), fill=MUTED, anchor="ls")
        rf = C._font("number", 20)
        for pp in chunk:
            n += 1
            if n % 2 == 0:
                d.rectangle((M, y, W - M, y + 44), fill=(246, 244, 238))
            vals = [str(n), timezone.localtime(pp.project.date).strftime("%d.%m.%Y"), pp.project.title,
                    region_label(pp.project.region, lang) if pp.project.region else "—", C.number_of(pp)]
            for (x, _t0, w), v in zip(cols, vals):
                d.text((x + 12, y + 29), _ellipsis(d, v, rf, w - 20), font=rf, fill=DARK, anchor="ls")
            y += 44
        d.line((M, H - 110, W - M, H - 110), fill=LINE, width=2)
        d.text((M, H - 75), _t("foot", lang).format(date=today), font=C._font("number", 18), fill=MUTED, anchor="ls")
        d.text((W - M, H - 75), f"yashilqollar.uz · {pi + 1}/{total_pages} {_t('page', lang)}", font=C._font("number", 18), fill=MUTED, anchor="rs")
        d.text((M, H - 45), f"CV-{user.id:06d}", font=C._font("number", 16), fill=LINE, anchor="ls")
        pages.append(img)
    buf = BytesIO()
    pages[0].save(buf, "PDF", resolution=150.0, save_all=True, append_images=pages[1:], quality=90)
    return buf.getvalue()


def filename(user) -> str:
    import re
    n = re.sub(r"[^\w\-]+", "_", C.display_name(user.fullname), flags=re.UNICODE).strip("_")[:40] or "volunteer"
    return f"Yashil_Qollar_CV_{n}.pdf"
