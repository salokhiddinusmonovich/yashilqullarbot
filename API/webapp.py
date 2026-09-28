"""
API для Telegram Mini App (фронт: ~/fronted/miniAppYashilQo'llar).

Скорость — главное:
  • вход (POST /login/telegram-webapp/) СРАЗУ возвращает все данные
    главного экрана — одно сетевое обращение при открытии приложения;
  • ответы маленькие, фото — уменьшенные копии (app_telegram/thumbs.py);
  • уведомления в Telegram уходят в фоне, ответ не ждёт Telegram.

Логика записи и отметки — общая с ботом: app_telegram/services.py.
"""
import hashlib
import hmac
import io
import json
import re
import time
from datetime import timedelta
from html import escape
from urllib.parse import parse_qsl

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, views
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from app_telegram import certificates, cv, impact, referrals, services, spots, waitlist, wrapped
from app_telegram.models import TGUser, EcoProject, ProjectParticipation
from app_telegram.telegram import send_in_background, is_channel_member
from app_telegram.thumbs import thumb_url
from tgbot.i18n import LANGS, t as bot_t, region_label, role_label, rank_label
from tgbot.services.lang import lang_of_sync, set_lang_sync
from .authentication import CustomRefreshToken, TGUserJWTAuthentication

INIT_DATA_MAX_AGE = 24 * 3600
RANK_STEPS = (150, 300)


# ─────────────────────────── проверка initData ───────────────────────────

def verify_init_data(init_data: str):
    """
    Проверка подписи Telegram Mini App:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    Возвращает dict с данными или None, если подпись неверна/устарела.
    """
    if not init_data:
        return None
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return None
    try:
        if time.time() - int(pairs.get("auth_date", 0)) > INIT_DATA_MAX_AGE:
            return None
        pairs["user"] = json.loads(pairs.get("user", "{}"))
    except (ValueError, TypeError):
        return None
    return pairs


# ─────────────────────────── сериализация ───────────────────────────

def _abs(request, url):
    return request.build_absolute_uri(url) if url else None


def _user_payload(request, user: TGUser, lang: str):
    attended = ProjectParticipation.objects.filter(user=user, status='attended').count()
    next_at = next((s for s in RANK_STEPS if user.balance < s), None)
    return {
        "id": user.id,
        "tg_id": user.tg_id,
        "username": user.username,
        "fullname": user.fullname,
        # анкета — для экрана «Изменить профиль»
        "email": user.email,
        "phone": user.phone,
        "age": user.age,
        "education_place": user.education_place,
        "experience": user.experience,
        # привязка к сайту
        "has_password": bool(user.password),
        "auth_provider": user.auth_provider,
        "photo": _abs(request, thumb_url(user.photo, 300)),
        "role": user.role,
        "role_label": role_label(user.role, lang),
        "is_staff": services.is_staff(user),
        "is_admin": user.is_admin,
        "balance": user.balance,
        "rank": rank_label(user.balance, lang),
        "rank_next_at": next_at,
        "region": user.region,
        "region_label": region_label(user.region, lang) if user.region else None,
        "attended_count": attended,
        "lang": lang,
    }


def _event_payload(request, p, joined_status=None, lang="uz"):
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description or "",
        "date": timezone.localtime(p.date).isoformat(),
        "location": p.location_name,
        "region": p.region,
        "region_label": region_label(p.region, lang),
        "photo": _abs(request, thumb_url(p.photo, 800)),
        "registered": getattr(p, "registered", None),
        "attended": getattr(p, "attended", None),
        "max": p.max_participants,
        "my_status": joined_status,
        # ⏳ лист ожидания: сколько в очереди и моё место (если стою)
        "waitlist": waitlist.count(p.id),
        "my_wait": waitlist.position(request.user.id, p.id) if getattr(request, "user", None) and request.user.is_authenticated and not joined_status else None,
        # ссылку на группу показываем только записавшимся
        "chat_link": p.chat_link if joined_status else None,
    }


def community_stats():
    """Общий вклад проекта — для блока «Наш вклад». Кэш 5 минут."""
    data = cache.get("webapp_community")
    if data is None:
        data = {
            "volunteers": TGUser.objects.count(),
            "events": EcoProject.objects.filter(date__lt=timezone.now()).count(),
            "checkins": ProjectParticipation.objects.filter(status='attended').count(),
            "regions": TGUser.objects.exclude(region__isnull=True).exclude(region='')
                       .values('region').annotate(n=Count('id')).count(),
        }
        cache.set("webapp_community", data, 300)
    # 📊 итоги мероприятий (кг/мешки/деревья) — свой кэш, обновляется сразу после ввода итогов
    tot = impact.totals()
    return {**data, "kg": tot["kg"], "bags": tot["bags"], "trees": tot["trees"], "photos": tot["photos"]}


def my_impact(user) -> dict:
    """«Mening hissam»: моя доля в итогах + последние фото с моих мероприятий."""
    pids = list(ProjectParticipation.objects.filter(user=user, status='attended').values_list('project_id', flat=True))
    return {**impact.share_of(user), "photos": impact.recent_photos(limit=8, pids=pids)}


def spots_summary(user) -> dict:
    """🗺 Эко-карта на главной: сколько мест ждут уборки, сколько убрано, сколько сообщил я."""
    items = spots.all_spots()
    return {"open": sum(1 for s in items if s["status"] in ("accepted", "planned")),
            "cleaned": sum(1 for s in items if s["status"] == "cleaned"),
            "mine": sum(1 for s in items if s.get("uid") == user.id)}


def wrapped_info(user, lang):
    """🎁 Итоги года: {year, url} — когда доступны (декабрь–январь; админам — всегда, как превью)."""
    preview = wrapped.can_preview(user)
    year = wrapped.year_for(preview=preview)
    if not year:
        return None
    return {"year": year, "image": wrapped.url(user.id, year, lang), "preview": preview and wrapped.year_for() is None}


def bootstrap_data(request, user: TGUser, lang: str = None):
    """Всё, что нужно главному экрану, — одним ответом."""
    lang = lang or (lang_of_sync(user.tg_id) if user.tg_id else "uz")
    now = timezone.now()

    my = {
        pp.project_id: pp.status
        for pp in ProjectParticipation.objects.filter(user=user).exclude(status='rejected').only('project_id', 'status')
    }

    upcoming_qs = services.with_counts(
        EcoProject.objects.filter(is_active=True, date__gte=now - timedelta(hours=6))
    )
    regions = services.region_group(user.region)
    # Показываем мероприятия своего региона + те, куда человек уже записан
    upcoming_qs = upcoming_qs.filter(Q(region__in=regions) | Q(id__in=list(my))).order_by('date')[:30]
    events = [_event_payload(request, p, my.get(p.id), lang) for p in upcoming_qs]

    history = list(
        ProjectParticipation.objects.filter(user=user, status='attended')
        .select_related('project').order_by('-project__date')[:80]
    )
    done = impact.many([pp.project_id for pp in history])

    return {
        "user": _user_payload(request, user, lang),
        "events": events,
        "history": [
            {"id": pp.project_id, "title": pp.project.title,
             "date": timezone.localtime(pp.project.date).isoformat(),
             "has_impact": pp.project_id in done,
             # 🎓 сертификат: pid — id участия, pdf/jpg — подписанные ссылки
             "cert": {"pid": pp.id, "number": certificates.number_of(pp),
                      "pdf": certificates.url(pp.id, "pdf"), "jpg": certificates.url(pp.id, "jpg") + "?small=1"}}
            for pp in history
        ],
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "cv_url": cv.url(user.id),
        "referral": {**referrals.stats(user.tg_id), "link": referrals.link(settings.TELEGRAM_BOT_USERNAME, user.tg_id)} if user.tg_id else None,
        "community": community_stats(),
        "impact": my_impact(user),
        "wrapped": wrapped_info(user, lang),
        "spots": spots_summary(user),
        "regions": [[code, region_label(code, lang)] for code in TGUser.Region.values],
    }


# ─────────────────────────── эндпоинты ───────────────────────────

class WebAppLoginView(views.APIView):
    """
    POST /login/telegram-webapp/   { init_data }
    → { access, refresh, registered: true, data: <bootstrap> }
    → { registered: false, bot_username }   — человека ещё нет в базе
      (регистрация остаётся в боте — там анкета, телефон, регион)
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = verify_init_data(request.data.get("init_data", ""))
        if not data or not data["user"].get("id"):
            return Response({"error": "invalid init_data"}, status=status.HTTP_401_UNAUTHORIZED)

        tg = data["user"]
        user = TGUser.objects.filter(tg_id=tg["id"]).first()
        if not user:
            return Response({"registered": False, "bot_username": settings.TELEGRAM_BOT_USERNAME})

        if tg.get("username") and tg["username"] != user.username:
            user.username = tg["username"]
            user.save(update_fields=["username"])

        refresh = CustomRefreshToken.for_user_obj(user)
        return Response({
            "registered": True,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "data": bootstrap_data(request, user),
        })


class PublicStatsView(views.APIView):
    """
    GET /stats/ — реальные цифры проекта для сайта (без входа):
    { volunteers, events, checkins, regions }. Кэш 5 минут.
    Вместо захардкоженных «1,000+ / 25+» на главной.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        resp = Response(community_stats())
        resp["Cache-Control"] = "public, max-age=300"
        return resp


class _Auth(views.APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TGUserJWTAuthentication]


class BootstrapView(_Auth):
    """GET /webapp/bootstrap/ — обновить данные (после записи, смены языка и т.п.)."""

    def get(self, request):
        return Response(bootstrap_data(request, request.user))


class MeView(_Auth):
    """
    PATCH /webapp/me/ — изменить анкету из Mini App.
    Ошибки: 400 {"errors": {поле: "required" | "invalid" | "taken" | "range"}}.
    Ответ — свежий bootstrap, чтобы приложение сразу обновило все экраны.
    """
    FIELDS = ("fullname", "region", "phone", "email", "age", "education_place", "experience")

    def patch(self, request):
        user, data, errors = request.user, request.data, {}
        changed = []

        def clean(v):
            return v.strip() if isinstance(v, str) else v

        if "fullname" in data:
            v = clean(data["fullname"]) or ""
            if len(v) < 2:
                errors["fullname"] = "required"
            else:
                user.fullname = v[:255]; changed.append("fullname")
        if "region" in data:
            v = clean(data["region"])
            if v not in TGUser.Region.values:
                errors["region"] = "invalid"
            else:
                user.region = v; changed.append("region")
        if "phone" in data:
            v = re.sub(r"[\s\-()]", "", clean(data["phone"]) or "")
            if v and not re.fullmatch(r"\+?\d{7,15}", v):
                errors["phone"] = "invalid"
            else:
                user.phone = v or None; changed.append("phone")
        if "email" in data:
            v = (clean(data["email"]) or "").lower()
            if v:
                try:
                    validate_email(v)
                except ValidationError:
                    errors["email"] = "invalid"
                else:
                    if TGUser.objects.filter(email__iexact=v).exclude(id=user.id).exists():
                        errors["email"] = "taken"
            if "email" not in errors:
                # None, а не "" — email unique, пустые строки у двух людей конфликтовали бы
                user.email = v or None; changed.append("email")
        if "age" in data:
            v = data["age"]
            if v in (None, ""):
                user.age = None; changed.append("age")
            else:
                try:
                    v = int(v)
                    if not 5 <= v <= 120:
                        raise ValueError
                    user.age = v; changed.append("age")
                except (TypeError, ValueError):
                    errors["age"] = "range"
        for f, limit in (("education_place", 255), ("experience", 2000)):
            if f in data:
                setattr(user, f, (clean(data[f]) or "")[:limit] or None); changed.append(f)

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        if changed:
            user.save(update_fields=changed)
        return Response(bootstrap_data(request, user))


class MePhotoView(_Auth):
    """POST /webapp/me/photo/ (multipart, поле photo) — новое фото профиля."""
    MAX_BYTES = 8 * 1024 * 1024

    def post(self, request):
        from PIL import Image, ImageOps
        from django.core.files.base import ContentFile

        f = request.FILES.get("photo")
        if not f or f.size > self.MAX_BYTES:
            return Response({"error": "too_big" if f else "required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with Image.open(f) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((1024, 1024))
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=85, optimize=True)
        except Exception:
            return Response({"error": "not_image"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.photo.save(f"user_{user.tg_id or user.id}_{int(time.time())}.jpg", ContentFile(buf.getvalue()), save=False)
        user.save(update_fields=["photo"])
        return Response(bootstrap_data(request, user))


class MePasswordView(_Auth):
    """
    POST /webapp/me/password/ { password } — пароль для входа на сайт
    (yashilqollar.uz) по email. Нужен email в профиле.
    """

    def post(self, request):
        user = request.user
        pw = request.data.get("password") or ""
        if not user.email:
            return Response({"error": "no_email"}, status=status.HTTP_400_BAD_REQUEST)
        if len(pw) < 8:
            return Response({"error": "short"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(pw)
        user.save(update_fields=["password"])
        return Response(bootstrap_data(request, user))


class AllEventsView(_Auth):
    """GET /webapp/events/ — ближайшие мероприятия ВСЕХ регионов (фильтр «Все регионы»)."""

    def get(self, request):
        user = request.user
        lang = lang_of_sync(user.tg_id) if user.tg_id else "uz"
        my = dict(
            ProjectParticipation.objects.filter(user=user).exclude(status='rejected')
            .values_list('project_id', 'status')
        )
        qs = services.with_counts(
            EcoProject.objects.filter(is_active=True, date__gte=timezone.now() - timedelta(hours=6))
        ).order_by('date')[:60]
        return Response({"events": [_event_payload(request, p, my.get(p.id), lang) for p in qs]})


class JoinView(_Auth):
    """POST /webapp/events/<id>/join/ → { result: ok|already|gone|full|region|subscribe, event }"""

    def post(self, request, pk):
        user = request.user
        if ProjectParticipation.objects.filter(user=user, project_id=pk).exists():
            return Response({"result": "already"})
        # регион проверяем ДО сетевого запроса к Telegram (подписка на канал)
        other = EcoProject.objects.filter(id=pk).values_list('region', flat=True).first()
        if other and other not in services.region_group(user.region):
            return Response({"result": "region"})
        if user.tg_id and not is_channel_member(user.tg_id):
            return Response({"result": "subscribe", "channel": "yashilqollar"})

        code, project = services.join_event(user, pk)
        if not project:
            return Response({"result": code})
        lang = lang_of_sync(user.tg_id) if user.tg_id else "uz"
        project = services.with_counts(EcoProject.objects.filter(id=project.id)).first()
        my_status = ProjectParticipation.objects.filter(user=user, project=project).values_list('status', flat=True).first()
        return Response({"result": code, "event": _event_payload(request, project, my_status, lang)})


class LangView(_Auth):
    """POST /webapp/lang/ { lang } — тот же язык, что и в боте."""

    def post(self, request):
        lang = request.data.get("lang")
        if lang not in LANGS or not request.user.tg_id:
            return Response({"error": "bad lang"}, status=status.HTTP_400_BAD_REQUEST)
        set_lang_sync(request.user.tg_id, lang)
        return Response(bootstrap_data(request, request.user, lang=lang))


class QRView(_Auth):
    """GET /webapp/qr.svg — личный QR (тот же, что в боте: t.me/<bot>?start=qr_<tg_id>)."""

    def get(self, request):
        import qrcode
        import qrcode.image.svg
        if not request.user.tg_id:
            return Response({"error": "no telegram"}, status=status.HTTP_400_BAD_REQUEST)
        link = f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start=qr_{request.user.tg_id}"
        img = qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=1)
        buf = io.BytesIO()
        img.save(buf)
        resp = HttpResponse(buf.getvalue(), content_type="image/svg+xml")
        resp["Cache-Control"] = "private, max-age=86400"
        return resp


ROLE_ORDER = ["Founder", "head_coordinator", "main_coordinator", "coordinator", "organizer", "it", "mobilograph"]


def _person(request, u: TGUser, lang: str):
    """Карточка человека для списков (рейтинг, команда) — только публичные поля."""
    return {
        "id": u.id,
        "fullname": u.fullname,
        "photo": _abs(request, thumb_url(u.photo, 160)),
        "role": u.role,
        "role_label": role_label(u.role, lang),
        "balance": u.balance,
    }


class PublicProfileView(_Auth):
    """
    GET /webapp/users/<id>/ — паспорт другого человека в Mini App.
    Только публичное: без телефона, email, username и Telegram ID.
    """

    def get(self, request, pk):
        u = TGUser.objects.filter(id=pk).first()
        if not u:
            return Response({"error": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        lang = lang_of_sync(request.user.tg_id) if request.user.tg_id else "uz"
        history = list(
            ProjectParticipation.objects.filter(user=u, status='attended')
            .select_related('project').order_by('-project__date')[:24]
        )
        next_at = next((s for s in RANK_STEPS if u.balance < s), None)
        return Response({
            **_person(request, u, lang),
            "photo": _abs(request, thumb_url(u.photo, 300)),
            "rank": rank_label(u.balance, lang),
            "rank_next_at": next_at,
            "region": u.region,
            "region_label": region_label(u.region, lang) if u.region else None,
            "attended_count": ProjectParticipation.objects.filter(user=u, status='attended').count(),
            "is_staff": services.is_staff(u),
            "history": [
                {"id": pp.project_id, "title": pp.project.title,
                 "date": timezone.localtime(pp.project.date).isoformat()}
                for pp in history
            ],
        })


class TeamView(_Auth):
    """
    GET /webapp/team/ — к кому обращаться: основатели (все) + команда
    своего региона (любая роль, кроме волонтёра). Основатели — первыми.
    """

    def get(self, request):
        lang = lang_of_sync(request.user.tg_id) if request.user.tg_id else "uz"
        regions = services.region_group(request.user.region)
        qs = TGUser.objects.exclude(role=TGUser.Role.VOLUNTEER).filter(
            Q(role="Founder") | Q(region__in=regions)
        ).only("id", "fullname", "photo", "role", "balance")
        people = sorted(qs, key=lambda u: (ROLE_ORDER.index(u.role) if u.role in ROLE_ORDER else 99, u.fullname))
        return Response({"team": [_person(request, u, lang) for u in people]})


class LeaderboardView(_Auth):
    """GET /webapp/top/ — топ-50 и моё место."""

    def get(self, request):
        top = list(
            TGUser.objects.filter(balance__gt=0).order_by('-balance', 'id')
            .only('id', 'fullname', 'photo', 'balance', 'region', 'role')[:50]
        )
        me = request.user
        my_place = TGUser.objects.filter(Q(balance__gt=me.balance) | Q(balance=me.balance, id__lt=me.id)).count() + 1
        return Response({
            "top": [
                {"id": u.id, "fullname": u.fullname, "balance": u.balance, "role": u.role,
                 "photo": _abs(request, thumb_url(u.photo, 120)), "me": u.id == me.id}
                for u in top
            ],
            "my_place": my_place,
            "my_balance": me.balance,
        })


# ─────────────────────────── координаторы ───────────────────────────

class _Staff(_Auth):
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not services.is_staff(request.user):
            self.permission_denied(request, message="staff only")


class StaffEventsView(_Staff):
    """
    GET /webapp/staff/events/ — мероприятия для сканирования (вчера…+7 дней) + какое выбрать по умолчанию.
    Только своего региона (services.scan_regions), у основателя — все.
    👑 is_admin — все регионы и прошедшие за 60 дней (отметить тех, кто забыл показать QR), новые первыми.
    """

    def get(self, request):
        now = timezone.now()
        lang = lang_of_sync(request.user.tg_id) if request.user.tg_id else "uz"
        back = services.scan_back_days(request.user)
        qs = EcoProject.objects.filter(date__gte=now - timedelta(days=back), date__lte=now + timedelta(days=7))
        allowed = services.scan_regions(request.user)
        if allowed is not None:
            qs = qs.filter(region__in=allowed)
        super_ = services.is_super_scanner(request.user)
        qs = services.with_counts(qs).order_by('-date' if super_ else 'date')[:60 if super_ else 20]
        events = [_event_payload(request, p, None, lang) for p in qs]
        today = timezone.localdate().isoformat()
        mine = services.region_group(request.user.region)
        default = next(
            (e["id"] for e in events if e["date"][:10] == today and e["region"] in mine),
            next((e["id"] for e in events if e["date"][:10] == today), events[0]["id"] if events else None),
        )
        return Response({"events": events, "default": default, "admin": super_})


class StaffCheckInView(_Staff):
    """
    POST /webapp/staff/checkin/  { project_id, qr } или { project_id, user_id }
    → { result: ok|already|not_found|bad_qr|other_region|wrong_region, auto_added, person, counts }
    Не записан — записывается автоматически (как и в боте).
    Мероприятие чужого региона — отказ (other_region), даже если id подставили вручную.
    Человек из другого региона, чем мероприятие — отказ (wrong_region), для всех, даже is_admin.
    """

    def post(self, request):
        project = EcoProject.objects.filter(id=request.data.get("project_id")).first()
        if not project:
            return Response({"result": "no_event"}, status=status.HTTP_400_BAD_REQUEST)
        if not services.can_scan_project(request.user, project):
            return Response({"result": "other_region"})

        if request.data.get("user_id"):
            volunteer = TGUser.objects.filter(id=request.data["user_id"]).first()
        else:
            tg_id = services.parse_qr(request.data.get("qr", ""))
            if not tg_id:
                return Response({"result": "bad_qr"})
            volunteer = TGUser.objects.filter(tg_id=tg_id).first()
        if not volunteer:
            return Response({"result": "not_found"})

        # Человек из другого региона — это ошибка (выбрано не то мероприятие): не отмечаем никому.
        if services.wrong_region(volunteer, project):
            already = ProjectParticipation.objects.filter(user=volunteer, project=project, status='attended').exists()
            if not already:
                lang = lang_of_sync(request.user.tg_id) if request.user.tg_id else "uz"
                return Response({
                    "result": "wrong_region",
                    "person": {"id": volunteer.id, "fullname": volunteer.fullname,
                               "photo": _abs(request, thumb_url(volunteer.photo, 120)), "balance": volunteer.balance},
                    "person_region": region_label(volunteer.region, lang),
                    "event_region": region_label(project.region, lang) if project.region else "",
                    "event_title": project.title,
                })

        result, auto_added = services.check_in(volunteer, project)
        volunteer.refresh_from_db(fields=['balance'])

        if result == "ok" and volunteer.tg_id:
            v_lang = lang_of_sync(volunteer.tg_id)
            send_in_background([(volunteer.tg_id, bot_t(
                "attended_notify", v_lang, project=escape(project.title), balance=volunteer.balance,
            ))])
            # отметили задним числом (мероприятие уже прошло) — сертификат сразу, не ждать утренней рассылки
            if project.date and project.date <= timezone.now() - timedelta(hours=2):
                pp = ProjectParticipation.objects.filter(user=volunteer, project=project, status='attended').first()
                if pp:
                    certificates.deliver_in_background(pp.id)

        counts = services.with_counts(EcoProject.objects.filter(id=project.id)).values('registered', 'attended').first()
        return Response({
            "result": result,
            "auto_added": auto_added,
            "person": {
                "id": volunteer.id,
                "fullname": volunteer.fullname,
                "photo": _abs(request, thumb_url(volunteer.photo, 120)),
                "balance": volunteer.balance,
            },
            "counts": counts,
        })


class StaffUndoView(_Staff):
    """POST /webapp/staff/undo/ { project_id, user_id, auto_added } — отменить последнюю отметку (ошибся мероприятием/человеком)."""

    def post(self, request):
        project = EcoProject.objects.filter(id=request.data.get("project_id")).first()
        volunteer = TGUser.objects.filter(id=request.data.get("user_id")).first()
        if not project or not volunteer or not services.can_scan_project(request.user, project):
            return Response({"result": "error"}, status=status.HTTP_400_BAD_REQUEST)
        done = services.undo_check_in(volunteer, project, bool(request.data.get("auto_added")))
        counts = services.with_counts(EcoProject.objects.filter(id=project.id)).values('registered', 'attended').first()
        return Response({"result": "undone" if done else "nothing", "counts": counts})


class StaffSearchView(_Staff):
    """GET /webapp/staff/search/?q=... — найти человека, у которого нет QR с собой."""

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()
        if len(q) < 2:
            return Response({"results": []})
        users = TGUser.objects.filter(services.user_search_q(q)).order_by('fullname')[:15]
        return Response({"results": [
            {"id": u.id, "fullname": u.fullname, "username": u.username,
             "photo": _abs(request, thumb_url(u.photo, 120))}
            for u in users
        ]})


# ─────────────────────────── эко-магазин (бета) ───────────────────────────
# Магазин ещё не открыт: товары и цены — на фронте (Mini App, screens/Shop.tsx).
# Здесь только «❤ Хочу» — чтобы до запуска знать, что и сколько заказывать.
# Хранится в Redis (db 6, как язык): shop:wish:<item> — множество tg_id. Схему БД не трогаем.

SHOP_ITEMS = ("stickers", "pin", "bracelet", "notebook", "bag", "cap", "tree", "tshirt", "thermos", "hoodie")


def _shop_state(tg_id):
    from tgbot.services.lang import _sclient
    r = _sclient()
    try:
        pipe = r.pipeline()
        for item in SHOP_ITEMS:
            pipe.scard(f"shop:wish:{item}")
            pipe.sismember(f"shop:wish:{item}", tg_id)
        res = pipe.execute()
    except Exception:
        return {"counts": {}, "mine": []}
    counts = {item: int(res[2 * i]) for i, item in enumerate(SHOP_ITEMS)}
    mine = [item for i, item in enumerate(SHOP_ITEMS) if res[2 * i + 1]]
    return {"counts": counts, "mine": mine}


class ShopView(_Auth):
    """GET /webapp/shop/ — сколько людей хотят каждый товар + мои «хочу». POST {item} — переключить «хочу»."""

    def get(self, request):
        return Response(_shop_state(request.user.tg_id))

    def post(self, request):
        item = request.data.get("item")
        if item not in SHOP_ITEMS or not request.user.tg_id:
            return Response({"detail": "bad item"}, status=status.HTTP_400_BAD_REQUEST)
        from tgbot.services.lang import _sclient
        key = f"shop:wish:{item}"
        try:
            r = _sclient()
            if r.sismember(key, request.user.tg_id):
                r.srem(key, request.user.tg_id)
            else:
                r.sadd(key, request.user.tg_id)
        except Exception:
            return Response({"detail": "unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(_shop_state(request.user.tg_id))


# ─────────────────────────── рейтинг регионов ───────────────────────────

def region_rating(lang="uz"):
    """Регионы по активности: отметки «пришёл» за этот месяц и всего. Ташкент город+область — вместе."""
    key = f"webapp:regions:{lang}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    month_start = timezone.localdate().replace(day=1)
    groups = [("tashkent", list(services.TASHKENT))] + [(c, [c]) for c in TGUser.Region.values if c not in services.TASHKENT]
    att = dict(ProjectParticipation.objects.filter(status='attended').values_list('project__region').annotate(n=Count('id')))
    att_m = dict(ProjectParticipation.objects.filter(status='attended', project__date__date__gte=month_start)
                 .values_list('project__region').annotate(n=Count('id')))
    vols = dict(TGUser.objects.exclude(region__isnull=True).values_list('region').annotate(n=Count('id')))
    rows = []
    for gkey, codes in groups:
        label = bot_t("rep_tashkent", lang) if gkey == "tashkent" else region_label(gkey, lang)
        rows.append({"key": gkey, "label": label,
                     "month": sum(att_m.get(c, 0) for c in codes), "total": sum(att.get(c, 0) for c in codes),
                     "volunteers": sum(vols.get(c, 0) for c in codes)})
    rows.sort(key=lambda r: (-r["month"], -r["total"], -r["volunteers"]))
    cache.set(key, rows, 600)
    return rows


class RegionsView(_Auth):
    """GET /webapp/regions/ — рейтинг регионов (кэш 10 минут) + мой регион."""

    def get(self, request):
        lang = lang_of_sync(request.user.tg_id) if request.user.tg_id else "uz"
        reg = request.user.region
        mine = "tashkent" if reg in services.TASHKENT else reg
        return Response({"regions": region_rating(lang), "mine": mine})


class CertificateSendView(_Auth):
    """POST /webapp/certificates/<pid>/send/ — бот присылает PDF сертификата в чат (только свой и только «пришёл»)."""

    def post(self, request, pid):
        from app_telegram.telegram import send_documents_in_background
        pp = certificates.attended(pid)
        if not pp or pp.user_id != request.user.id or not request.user.tg_id:
            return Response({"result": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        lang = lang_of_sync(request.user.tg_id)
        tg, title = request.user.tg_id, pp.project.title

        def build():
            p2 = certificates.attended(pid)
            return [(tg, certificates.to_pdf(certificates.render_for(p2)), certificates.filename(p2),
                     bot_t("cert_caption", lang, title=escape(title), number=certificates.number_of(p2)))]
        send_documents_in_background(build)
        return Response({"result": "sent"})


class WaitView(_Auth):
    """POST /webapp/events/<id>/wait/ {leave?: true} — встать в очередь на заполненное мероприятие / выйти."""

    def post(self, request, pk):
        user = request.user
        project = services.with_counts(EcoProject.objects.filter(id=pk, is_active=True)).first()
        if not project:
            return Response({"result": "gone"})
        if request.data.get("leave"):
            waitlist.leave(user.id, pk)
            result = "left"
        else:
            if project.region not in services.region_group(user.region):
                return Response({"result": "region"})
            if ProjectParticipation.objects.filter(user=user, project=project).exists():
                return Response({"result": "already"})
            waitlist.join(user, project)
            result = "waiting"
        lang = lang_of_sync(user.tg_id) if user.tg_id else "uz"
        return Response({"result": result, "event": _event_payload(request, project, None, lang)})


# ─────────────────────────── 📊 итоги мероприятий и 🎁 итоги года ───────────────────────────

class ImpactEventView(_Auth):
    """GET /webapp/impact/<id>/ — итоги мероприятия: цифры, сколько пришло, все фото, моя доля."""

    def get(self, request, pk):
        p = EcoProject.objects.filter(id=pk).first()
        data = impact.event_payload(p) if p else None
        if not data:
            return Response({"result": "none"}, status=status.HTTP_404_NOT_FOUND)
        was = ProjectParticipation.objects.filter(user=request.user, project=p, status='attended').exists()
        n = max(data["attended"], 1)
        mine = {k: round(data[k] / n, 1) for k in impact.KINDS} if was else None
        return Response({"id": p.id, "title": p.title, "date": timezone.localtime(p.date).isoformat(),
                         "region_label": region_label(p.region, lang_of_sync(request.user.tg_id) if request.user.tg_id else "uz"),
                         **data, "mine": mine})


class WrappedView(_Auth):
    """GET /webapp/wrapped/ — 🎁 итоги года для сторис в Mini App (404, если ещё не время)."""

    def get(self, request):
        user = request.user
        lang = lang_of_sync(user.tg_id) if user.tg_id else "uz"
        info = wrapped_info(user, lang)
        if not info:
            return Response({"result": "soon"}, status=status.HTTP_404_NOT_FOUND)
        s = wrapped.stats(user, info["year"])
        s.pop("region", None)
        return Response({**s, **info, "region_label": region_label(user.region, lang) if user.region else None})


class PublicImpactView(views.APIView):
    """GET /impact/ — для сайта: итоги (кг/мешки/деревья) и последние фото с мероприятий. Кэш 5 минут."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        limit = min(int(request.query_params.get("limit") or 24), 60)
        resp = Response({**impact.totals(), "items": impact.recent_photos(limit=limit)})
        resp["Cache-Control"] = "public, max-age=300"
        return resp


# ─────────────────────────── 📍 Iflos joy / 🗺 эко-карта ───────────────────────────

class SpotsView(_Auth):
    """
    GET  /webapp/spots/ — точки для эко-карты: проверенные всем + свои (любой статус).
    POST /webapp/spots/ — 📍 сообщить о грязном месте прямо из Mini App (JSON):
         tokens (1–5 фото, загруженных через /webapp/spots/photo/), lat, lon, size, kind, access, note,
         force=true (не спрашивать про место рядом)
         → {result: ok, spot} | near {spot} | not_uz | limit {n} | bad
    Админам (галочка is_admin) бот присылает ту же карточку, что и из чата.
    """

    def get(self, request):
        user = request.user
        lang = lang_of_sync(user.tg_id) if user.tg_id else "uz"
        items = [spots.payload(s, lang, user) for s in spots.all_spots() if spots.visible_to(s, user)]
        return Response({"spots": items})

    def post(self, request):
        from asgiref.sync import async_to_sync
        from app_telegram.telegram import run_with_bot_in_background
        from tgbot.services import geo
        user = request.user
        lang = lang_of_sync(user.tg_id) if user.tg_id else "uz"
        d = request.data
        tokens = [x for x in (d.get("tokens") or []) if isinstance(x, str)][:spots.MAX_PHOTOS]
        try:
            lat, lon = float(d.get("lat")), float(d.get("lon"))
        except (TypeError, ValueError):
            return Response({"result": "bad", "field": "location"}, status=status.HTTP_400_BAD_REQUEST)
        size, kind, access = d.get("size"), d.get("kind"), d.get("access") or "unknown"
        if not tokens or size not in spots.SIZES or kind not in spots.KINDS or access not in spots.ACCESS:
            return Response({"result": "bad"}, status=status.HTTP_400_BAD_REQUEST)
        if not spots.can_report(user.tg_id or user.id):
            return Response({"result": "limit", "n": spots.PER_DAY})
        g = async_to_sync(geo.reverse)(lat, lon, lang)
        if (g and g["country"] and g["country"] != "uz") or (not g and not spots.in_uz_box(lat, lon)):
            return Response({"result": "not_uz"})
        if d.get("force") not in (True, "1", "true"):
            near = spots.near_open(lat, lon)
            if near:
                return Response({"result": "near", "spot": spots.payload(near, lang, user)})
        s = spots.create(user, lat, lon, (g or {}).get("region") or spots.nearest_region(lat, lon), size, kind, access,
                         (d.get("note") or "")[:500], (g or {}).get("address", ""), tokens=tokens)
        if not s["photos"]:
            return Response({"result": "bad", "field": "photos"}, status=status.HTTP_400_BAD_REQUEST)

        async def notify(bot):
            from tgbot.handlers.spots import notify_moderators
            await notify_moderators(bot, s, None, user)
        run_with_bot_in_background(notify)
        return Response({"result": "ok", "spot": spots.payload(s, lang, user)})


class SpotPhotoView(_Auth):
    """POST /webapp/spots/photo/ (multipart photo) — загрузить одно фото заранее → {token}."""

    def post(self, request):
        f = request.FILES.get("photo")
        if not f or f.size > 15 * 1024 * 1024:
            return Response({"result": "bad"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response({"token": spots.save_tmp_photo(request.user.id, f.read())})
        except Exception:
            return Response({"result": "bad"}, status=status.HTTP_400_BAD_REQUEST)


class SpotConfirmView(_Auth):
    """POST /webapp/spots/<id>/confirm/ — «да, это то же место, всё ещё грязно» (+1 к подтверждениям)."""

    def post(self, request, pk):
        s = spots.get(pk)
        if not s or s["status"] not in spots.OPEN:
            return Response({"result": "none"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"result": "ok", "confirms": spots.confirm(pk, request.user.tg_id or -request.user.id)})


class SpotView(_Auth):
    """GET /webapp/spots/<id>/ — место целиком: фото, «до / после», мероприятие."""

    def get(self, request, pk):
        user = request.user
        s = spots.get(pk)
        if not s or not (spots.visible_to(s, user) or spots.can_moderate(user, s)):
            return Response({"result": "none"}, status=status.HTTP_404_NOT_FOUND)
        lang = lang_of_sync(user.tg_id) if user.tg_id else "uz"
        return Response(spots.payload(s, lang, user, full=True))


class PublicSpotsView(views.APIView):
    """GET /spots/ — для сайта: проверенные места (без авторов). Кэш 5 минут."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        lang = request.query_params.get("lang") if request.query_params.get("lang") in LANGS else "uz"
        items = []
        for s in spots.all_spots(spots.PUBLIC):
            p = spots.payload(s, lang)
            p.pop("mine", None)
            items.append(p)
        resp = Response({"spots": items, "counts": {k: sum(1 for x in items if x["status"] == k) for k in spots.PUBLIC}})
        resp["Cache-Control"] = "public, max-age=300"
        return resp
