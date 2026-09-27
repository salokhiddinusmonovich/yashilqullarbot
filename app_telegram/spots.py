"""
📍 Iflos joy — волонтёр сообщает о замусоренном месте; 🗺 эко-карта всех таких мест.

Поток: бот (tgbot/handlers/spots.py) спрашивает фото → геолокацию → регион → сколько/какой мусор →
можно ли подойти → комментарий, и присылает карточку админам + координаторам региона с кнопками
✅ Qabul · ❌ Rad · 📅 Tadbir · 🔁 Dublikat · 🧹 Tozalandi. Автору — статусы и баллы:
+5, когда место принято, +10, когда убрано. Когда координатор вносит итоги мероприятия, созданного
из этого места (/natija), место само становится «убрано», а автору приходит «до / после».

Статусы: new → accepted → planned → cleaned; rejected; duplicate.
На публичной карте — только проверенные (accepted / planned / cleaned); свои — автор видит всегда.

Хранение — Redis db 6 (схему БД не трогаем):
  spot:seq                 счётчик id
  spot:<id>                hash  поля ниже (photos / after — JSON-списки путей в MEDIA_ROOT)
  spot:all                 zset  id → время создания
  spot:ev:<id мероприятия> set   места, для которых создано мероприятие
  spot:conf:<id>           set   tg_id тех, кто подтвердил «всё ещё грязно»
  spot:rl:<tg>:<дата>      сколько сообщений человек прислал сегодня
"""
import json
import math
import time
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone
from PIL import Image, ImageOps

from .certificates import PUBLIC_URL

STATUSES = ("new", "accepted", "planned", "cleaned", "rejected", "duplicate")
OPEN = ("new", "accepted", "planned")
PUBLIC = ("accepted", "planned", "cleaned")
SIZES = ("small", "medium", "large")
KINDS = ("household", "plastic", "construction", "mixed")
ACCESS = ("easy", "hard", "unknown")
REASONS = ("clean", "unclear", "private", "other")
MAX_PHOTOS = 5
PER_DAY = int(__import__("os").environ.get("SPOT_PER_DAY", "3"))
NEAR_M = 100
POINTS_ACCEPTED, POINTS_CLEANED = 5, 10

# Узбекистан: ISO 3166-2 (так отвечает OpenStreetMap) → наши коды регионов
ISO_REGION = {
    "UZ-QR": "karakalpakstan", "UZ-AN": "andijon", "UZ-BU": "bukhara", "UZ-FA": "fargona", "UZ-JI": "jizzakh",
    "UZ-XO": "khorezm", "UZ-NG": "namangan", "UZ-NW": "navoi", "UZ-QA": "qashqadaryo", "UZ-SA": "samarkand",
    "UZ-SI": "sirdaryo", "UZ-SU": "surkhandaryo", "UZ-TO": "tashkent_v", "UZ-TK": "tashkent_s",
}
# центры регионов — запасной вариант, если OpenStreetMap не ответил (тогда регион человек подтверждает сам)
CENTERS = {
    "karakalpakstan": (42.46, 59.61), "andijon": (40.78, 72.34), "bukhara": (39.77, 64.42), "fargona": (40.39, 71.78),
    "jizzakh": (40.12, 67.84), "khorezm": (41.55, 60.63), "namangan": (41.00, 71.67), "navoi": (40.10, 65.37),
    "qashqadaryo": (38.86, 65.79), "samarkand": (39.65, 66.96), "sirdaryo": (40.49, 68.78), "surkhandaryo": (37.22, 67.28),
    "tashkent_v": (41.00, 69.60), "tashkent_s": (41.31, 69.28),
}
UZ_BBOX = (37.1, 45.6, 55.9, 73.2)      # lat min/max, lon min/max


def _r():
    from tgbot.services.lang import _sclient
    return _sclient()


def distance_m(a_lat, a_lon, b_lat, b_lon) -> float:
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def in_uz_box(lat, lon) -> bool:
    return UZ_BBOX[0] <= lat <= UZ_BBOX[1] and UZ_BBOX[2] <= lon <= UZ_BBOX[3]


def nearest_region(lat, lon) -> str:
    return min(CENTERS, key=lambda c: distance_m(lat, lon, *CENTERS[c]))


def maps_links(lat, lon) -> dict:
    return {"google": f"https://maps.google.com/?q={lat:.6f},{lon:.6f}",
            "yandex": f"https://yandex.uz/maps/?pt={lon:.6f},{lat:.6f}&z=17&l=map"}


# ─────────── хранение ───────────

def _decode(sid: int, h: dict) -> dict | None:
    if not h:
        return None
    s = dict(h)
    s["id"] = sid
    for k in ("lat", "lon"):
        s[k] = float(s.get(k) or 0)
    for k in ("tg", "uid", "created", "updated", "event_id", "handled_by"):
        s[k] = int(s.get(k) or 0)
    for k in ("photos", "after"):
        try:
            s[k] = json.loads(s.get(k) or "[]")
        except ValueError:
            s[k] = []
    return s


def get(sid: int) -> dict | None:
    try:
        r = _r()
        s = _decode(sid, r.hgetall(f"spot:{sid}"))
        if s:
            s["confirms"] = r.scard(f"spot:conf:{sid}")
        return s
    except Exception:
        return None


def all_spots(statuses=None) -> list:
    """Все места, новые первыми (статусы — фильтр)."""
    try:
        r = _r()
        ids = [int(x) for x in r.zrevrange("spot:all", 0, -1)]
        pipe = r.pipeline()
        for sid in ids:
            pipe.hgetall(f"spot:{sid}")
            pipe.scard(f"spot:conf:{sid}")
        res = pipe.execute()
    except Exception:
        return []
    out = []
    for i, sid in enumerate(ids):
        s = _decode(sid, res[2 * i])
        if s and (not statuses or s.get("status") in statuses):
            s["confirms"] = res[2 * i + 1]
            out.append(s)
    return out


def counts() -> dict:
    c = {k: 0 for k in STATUSES}
    for s in all_spots():
        c[s["status"]] = c.get(s["status"], 0) + 1
    return c


def can_report(tg: int) -> bool:
    try:
        return int(_r().get(f"spot:rl:{tg}:{timezone.localdate().isoformat()}") or 0) < PER_DAY
    except Exception:
        return True


def near_open(lat, lon, radius=NEAR_M) -> dict | None:
    """Уже есть открытое сообщение рядом? — чтобы не плодить дубликаты."""
    best = None
    for s in all_spots(OPEN):
        d = distance_m(lat, lon, s["lat"], s["lon"])
        if d <= radius and (best is None or d < best[0]):
            best = (d, s)
    return best[1] if best else None


def confirm(sid: int, tg: int) -> int:
    r = _r()
    r.sadd(f"spot:conf:{sid}", tg)
    return r.scard(f"spot:conf:{sid}")


def save_jpeg(data: bytes, rel: str, size=1600) -> str:
    dst = Path(settings.MEDIA_ROOT) / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(BytesIO(data)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((size, size))
        im.save(dst, "JPEG", quality=84, optimize=True, progressive=True)
    return rel


def create(user, lat, lon, region, size, kind, access, note="", address="", photos: list[bytes] = ()) -> dict:
    r = _r()
    sid = int(r.incr("spot:seq"))
    rels = [save_jpeg(p, f"spots/{sid}/{uuid.uuid4().hex[:10]}.jpg") for p in list(photos)[:MAX_PHOTOS]]
    now = int(time.time())
    r.hset(f"spot:{sid}", mapping={
        "tg": user.tg_id or 0, "uid": user.id, "name": user.fullname or "", "lat": f"{lat:.6f}", "lon": f"{lon:.6f}",
        "region": region or "", "size": size, "kind": kind, "access": access, "note": (note or "")[:500],
        "address": (address or "")[:300], "photos": json.dumps(rels), "after": "[]", "status": "new",
        "created": now, "updated": now,
    })
    r.zadd("spot:all", {sid: now})
    key = f"spot:rl:{user.tg_id}:{timezone.localdate().isoformat()}"
    r.incr(key)
    r.expire(key, 2 * 86400)
    return get(sid)


# ─────────── модерация ───────────

def can_moderate(user, spot: dict) -> bool:
    """Админ (is_admin), основатель — всё; координатор и др. команда — места своего региона."""
    from . import services
    if not user:
        return False
    if user.is_admin or user.role == "Founder":
        return True
    if not services.is_staff(user):
        return False
    allowed = services.scan_regions(user)
    return allowed is None or spot.get("region") in allowed


def moderators_for(region: str) -> list:
    """Кому приходит новое сообщение: все админы и основатели + координаторы/организаторы региона."""
    from . import services
    from .models import TGUser
    qs = TGUser.objects.filter(tg_id__isnull=False).filter(
        Q(is_admin=True) | Q(role=TGUser.Role.FOUNDER)
        | (Q(region__in=services.region_group(region)) & (Q(role__icontains="coordinator") | Q(role="organizer")))
    )
    return list(qs.distinct())


def _award(uid: int, n: int):
    from .models import TGUser
    TGUser.objects.filter(id=uid).update(balance=F('balance') + n)


def set_status(sid: int, status: str, by_tg: int = 0, reason: str = "", event_id: int = 0) -> tuple[dict | None, int]:
    """Сменить статус. → (место, сколько баллов начислено автору сейчас). Баллы — один раз за «принято» и «убрано»."""
    assert status in STATUSES
    r = _r()
    s = get(sid)
    if not s:
        return None, 0
    upd = {"status": status, "updated": int(time.time()), "handled_by": by_tg or 0}
    if reason:
        upd["reason"] = reason
    if event_id:
        upd["event_id"] = event_id
        r.sadd(f"spot:ev:{event_id}", sid)
    r.hset(f"spot:{sid}", mapping=upd)
    pts = 0
    if status in ("accepted", "planned", "cleaned") and r.hsetnx(f"spot:{sid}", "pts_acc", 1):
        pts += POINTS_ACCEPTED
    if status == "cleaned" and r.hsetnx(f"spot:{sid}", "pts_clean", 1):
        pts += POINTS_CLEANED
    if pts and s.get("uid"):
        _award(s["uid"], pts)
    return get(sid), pts


def next_saturday(now=None) -> datetime:
    d = timezone.localtime(now or timezone.now())
    days = (5 - d.weekday()) % 7 or 7
    return (d + timedelta(days=days)).replace(hour=10, minute=0, second=0, microsecond=0)


def create_event(sid: int, by_tg: int = 0):
    """📅 Черновик мероприятия (выключен — админ проверяет дату и включает). → (мероприятие, баллы)."""
    from tgbot.i18n import region_label
    from .models import EcoProject
    s = get(sid)
    if not s:
        return None, 0
    if s.get("event_id"):
        p = EcoProject.objects.filter(id=s["event_id"]).first()
        if p:
            return p, 0
    place = (s.get("address") or "").split(",")[0].strip() or region_label(s["region"], "uz")
    links = maps_links(s["lat"], s["lon"])
    p = EcoProject.objects.create(
        title=f"Tozalash: {place}"[:255], date=next_saturday(), is_active=False, max_participants=40,
        location_name=(s.get("address") or f"{s['lat']:.5f}, {s['lon']:.5f}")[:255],
        region=s["region"] or "tashkent_s",
        description=f"📍 Volontyor xabari #{sid}: {s.get('note') or ''}\n🗺 {links['google']}".strip(),
    )
    _, pts = set_status(sid, "planned", by_tg, event_id=p.id)
    return p, pts


def on_event_results(pid: int) -> list:
    """Итоги мероприятия внесены → места, для которых оно было, — «убрано», фото «после» = фото итогов.
    → [(место, баллы)] — кому написать «до / после»."""
    from . import impact
    try:
        ids = [int(x) for x in _r().smembers(f"spot:ev:{pid}")]
    except Exception:
        return []
    after = impact.get(pid).get("photos", [])[:4]
    out = []
    for sid in ids:
        s = get(sid)
        if not s or s["status"] == "cleaned":
            continue
        if after:
            _r().hset(f"spot:{sid}", "after", json.dumps(after))
        s2, pts = set_status(sid, "cleaned")
        out.append((s2, pts))
    return out


def author_text(s: dict, pts: int = 0, reason: str = "", event=None, lang: str = "uz") -> str:
    """Что написать автору о его сообщении (бот и админка — один текст)."""
    from html import escape
    from tgbot.i18n import t
    st = s["status"]
    if st == "planned" and event:
        text = t("spot_n_planned", lang, id=s["id"], title=escape(event.title), date=timezone.localtime(event.date).strftime("%d.%m"))
    elif st == "rejected":
        text = t("spot_n_rejected", lang, id=s["id"], reason=t(f"spot_rr_{reason or s.get('reason') or 'other'}", lang))
    else:
        text = t(f"spot_n_{st}", lang, id=s["id"])
    if pts:
        text += "\n" + t("spot_pts", lang, pts=pts)
    return text


# ─────────── для Mini App и сайта ───────────

def photo_url(rel: str) -> str:
    return f"{PUBLIC_URL}{settings.MEDIA_URL.rstrip('/')}/{rel}"


def payload(s: dict, lang: str = "uz", viewer=None, full=False) -> dict:
    from tgbot.i18n import region_label
    out = {
        "id": s["id"], "lat": s["lat"], "lon": s["lon"], "status": s["status"],
        "region": s.get("region"), "region_label": region_label(s["region"], lang) if s.get("region") else "",
        "size": s.get("size"), "kind": s.get("kind"), "created": s["created"], "confirms": s.get("confirms", 0),
        "photo": photo_url(s["photos"][0]) if s["photos"] else None,
        "mine": bool(viewer and s.get("uid") == viewer.id),
    }
    if full:
        from .models import EcoProject
        p = EcoProject.objects.filter(id=s["event_id"]).first() if s.get("event_id") else None
        out.update({
            "photos": [photo_url(x) for x in s["photos"]], "after": [photo_url(x) for x in s["after"]],
            "access": s.get("access"), "note": s.get("note") or "", "address": s.get("address") or "",
            "maps": maps_links(s["lat"], s["lon"]), "updated": s["updated"],
            "event": {"id": p.id, "title": p.title, "date": timezone.localtime(p.date).isoformat(), "active": p.is_active} if p else None,
        })
    return out


def visible_to(s: dict, viewer) -> bool:
    return s["status"] in PUBLIC or bool(viewer and s.get("uid") == viewer.id)
