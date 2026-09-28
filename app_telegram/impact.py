"""
📊 Итоги мероприятия: сколько собрали/посадили + фото.

Вводит координатор в боте (/natija или кнопка, которая приходит после мероприятия).
Видят: волонтёры (Mini App — «Mening hissam», галерея), сайт (/stats/, /impact/photos/),
итоги года (app_telegram/wrapped.py).

Хранение — Redis db 6 (схему БД не трогаем, как у листа ожидания и магазина):
  imp:<id мероприятия>     hash  kg / bags / trees / by / at
  imp:ph:<id мероприятия>  list  пути фото относительно MEDIA_ROOT (impact/<id>/<uuid>.jpg)
  imp:events               set   мероприятия, у которых есть итоги
«Мой вклад» = итог мероприятия / число пришедших — поровну на всех, кто был.
"""
import time
from datetime import timedelta
import uuid
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from PIL import Image, ImageOps

from .certificates import PUBLIC_URL

KINDS = ("kg", "bags", "trees")
MAX_PHOTOS = 30
MAX_VALUE = 1_000_000
TOTALS_KEY = "impact:totals"


def _r():
    from tgbot.services.lang import _sclient
    return _sclient()


def _num(kind, v):
    v = float(v or 0)
    return round(v, 1) if kind == "kg" else int(v)


def get(pid: int) -> dict:
    """{kg, bags, trees, photos: [пути], by, at} — пустой dict, если итогов нет."""
    try:
        r = _r()
        h = r.hgetall(f"imp:{pid}")
        photos = r.lrange(f"imp:ph:{pid}", 0, -1)
    except Exception:
        return {}
    if not h and not photos:
        return {}
    out = {k: _num(k, h.get(k)) for k in KINDS}
    out.update(photos=photos, by=int(h.get("by") or 0), at=int(h.get("at") or 0))
    return out


def many(pids) -> dict:
    """{pid: итоги} — одним заходом в Redis (для истории и итогов года)."""
    pids = list(pids)
    if not pids:
        return {}
    try:
        pipe = _r().pipeline()
        for pid in pids:
            pipe.hgetall(f"imp:{pid}")
            pipe.lrange(f"imp:ph:{pid}", 0, -1)
        res = pipe.execute()
    except Exception:
        return {}
    out = {}
    for i, pid in enumerate(pids):
        h, photos = res[2 * i], res[2 * i + 1]
        if h or photos:
            out[pid] = {**{k: _num(k, h.get(k)) for k in KINDS}, "photos": photos}
    return out


def save(pid: int, by_tg: int | None = None, **values):
    """Сохранить цифры (только переданные). Отрицательное/огромное — отбрасываем."""
    clean = {}
    for k in KINDS:
        if values.get(k) is not None:
            v = _num(k, values[k])
            if 0 <= v <= MAX_VALUE:
                clean[k] = v
    r = _r()
    if clean:
        r.hset(f"imp:{pid}", mapping={**clean, "by": by_tg or 0, "at": int(time.time())})
    r.sadd("imp:events", pid)
    cache.delete(TOTALS_KEY)


def add_photo(pid: int, data: bytes) -> str | None:
    """Сохранить фото (уменьшаем до 1600px, JPEG). Возвращает путь или None, если уже MAX_PHOTOS."""
    r = _r()
    if r.llen(f"imp:ph:{pid}") >= MAX_PHOTOS:
        return None
    rel = f"impact/{pid}/{uuid.uuid4().hex[:12]}.jpg"
    dst = Path(settings.MEDIA_ROOT) / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(BytesIO(data)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((1600, 1600))
        im.save(dst, "JPEG", quality=84, optimize=True, progressive=True)
    r.rpush(f"imp:ph:{pid}", rel)
    r.sadd("imp:events", pid)
    cache.delete(TOTALS_KEY)
    return rel


def clear_photos(pid: int):
    r = _r()
    for rel in r.lrange(f"imp:ph:{pid}", 0, -1):
        try:
            (Path(settings.MEDIA_ROOT) / rel).unlink()
        except OSError:
            pass
    r.delete(f"imp:ph:{pid}")
    cache.delete(TOTALS_KEY)


def photo_url(rel: str, width: int | None = None) -> str:
    """Полное фото или уменьшенная копия width px (Mini App и сайт грузят копии — быстрее)."""
    if width:
        from .thumbs import thumb_rel_url
        return f"{PUBLIC_URL}{thumb_rel_url(rel, width)}"
    return f"{PUBLIC_URL}{settings.MEDIA_URL.rstrip('/')}/{rel}"


def has_numbers(res: dict) -> bool:
    return any(res.get(k) for k in KINDS)


def summary(res: dict, lang=None) -> str:
    """«120 kg · 40 qop · 15 ko'chat» — только ненулевое."""
    from tgbot.i18n import t
    parts = [t(f"imp_u_{k}", lang, n=_fmt(res[k])) for k in KINDS if res.get(k)]
    return " · ".join(parts)


def _fmt(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


# ─────────── всего / моё ───────────

def _attended_counts(pids) -> dict:
    from .models import ProjectParticipation
    return dict(ProjectParticipation.objects.filter(project_id__in=pids, status='attended')
                .values_list('project_id').annotate(n=Count('id')))


def totals() -> dict:
    """Итог проекта для сайта и «Наш вклад»: {kg, bags, trees, events, photos}. Кэш 5 минут."""
    data = cache.get(TOTALS_KEY)
    if data is None:
        try:
            pids = [int(x) for x in _r().smembers("imp:events")]
        except Exception:
            pids = []
        res = many(pids)
        data = {k: _num(k, sum(v[k] for v in res.values())) for k in KINDS}
        data["events"] = sum(1 for v in res.values() if has_numbers(v))
        data["photos"] = sum(len(v["photos"]) for v in res.values())
        cache.set(TOTALS_KEY, data, 300)
    return data


def share_of(user, year: int | None = None) -> dict:
    """Мой вклад: {kg, bags, trees, events} — доля в итогах мероприятий, где я был (за год или всего)."""
    from .models import ProjectParticipation
    qs = ProjectParticipation.objects.filter(user=user, status='attended')
    if year:
        qs = qs.filter(project__date__year=year)
    pids = list(qs.values_list('project_id', flat=True))
    res = many(pids)
    out = {k: 0.0 for k in KINDS}
    counts = _attended_counts(list(res))
    events = 0
    for pid, v in res.items():
        n = max(counts.get(pid, 1), 1)
        if has_numbers(v):
            events += 1
        for k in KINDS:
            out[k] += v[k] / n
    return {"kg": round(out["kg"], 1), "bags": round(out["bags"], 1), "trees": round(out["trees"], 1), "events": events}


def recent_photos(limit=24, pids=None) -> list:
    """Последние фото с мероприятий (новые мероприятия первыми): [{url, event, title, date}]."""
    from .models import EcoProject
    if pids is None:
        try:
            pids = [int(x) for x in _r().smembers("imp:events")]
        except Exception:
            pids = []
    events = {p.id: p for p in EcoProject.objects.filter(id__in=pids).only('id', 'title', 'date')}
    res = many([pid for pid in events])
    out = []
    for p in sorted(events.values(), key=lambda p: p.date, reverse=True):
        for rel in res.get(p.id, {}).get("photos", []):
            out.append({"url": photo_url(rel, 400), "event": p.id, "title": p.title,
                        "date": timezone.localtime(p.date).date().isoformat()})
            if len(out) >= limit:
                return out
    return out


def event_payload(project) -> dict | None:
    """Итоги одного мероприятия для Mini App/сайта (None — нет итогов)."""
    res = get(project.id)
    if not res:
        return None
    attended = _attended_counts([project.id]).get(project.id, 0)
    return {**{k: res[k] for k in KINDS}, "attended": attended, "photos": [photo_url(p, 1000) for p in res["photos"]]}


# ─────────── кому напомнить ввести итоги ───────────

def recent_for_staff(user, days=14) -> list:
    """Прошедшие мероприятия (за days дней), которые этот человек может заполнять — новые первыми."""
    from . import services
    from .models import EcoProject
    now = timezone.now()
    qs = EcoProject.objects.filter(date__lte=now, date__gte=now - timedelta(days=days))
    allowed = services.scan_regions(user)
    if allowed is not None:
        qs = qs.filter(region__in=allowed)
    return list(qs.order_by('-date')[:12])


def reporters_for(project) -> list:
    """Кому прислать «введите итоги»: команда региона мероприятия (не волонтёры и не основатели)."""
    from . import services
    from .models import TGUser
    return list(TGUser.objects.filter(region__in=services.region_group(project.region), tg_id__isnull=False)
                .exclude(role__in=[TGUser.Role.VOLUNTEER, TGUser.Role.FOUNDER])
                .filter(Q(role__icontains="coordinator") | Q(role="organizer")))
