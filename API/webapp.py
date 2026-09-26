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

from app_telegram import services
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
    return data


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
        .select_related('project').order_by('-project__date')[:20]
    )

    return {
        "user": _user_payload(request, user, lang),
        "events": events,
        "history": [
            {"id": pp.project_id, "title": pp.project.title,
             "date": timezone.localtime(pp.project.date).isoformat()}
            for pp in history
        ],
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
        "community": community_stats(),
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


class LeaderboardView(_Auth):
    """GET /webapp/top/ — топ-50 и моё место."""

    def get(self, request):
        top = list(
            TGUser.objects.filter(balance__gt=0).order_by('-balance', 'id')
            .only('id', 'fullname', 'photo', 'balance', 'region')[:50]
        )
        me = request.user
        my_place = TGUser.objects.filter(Q(balance__gt=me.balance) | Q(balance=me.balance, id__lt=me.id)).count() + 1
        return Response({
            "top": [
                {"id": u.id, "fullname": u.fullname, "balance": u.balance,
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
    """GET /webapp/staff/events/ — мероприятия для сканирования (вчера…+7 дней) + какое выбрать по умолчанию."""

    def get(self, request):
        now = timezone.now()
        lang = lang_of_sync(request.user.tg_id) if request.user.tg_id else "uz"
        qs = services.with_counts(
            EcoProject.objects.filter(date__gte=now - timedelta(days=1), date__lte=now + timedelta(days=7))
        ).order_by('date')[:20]
        events = [_event_payload(request, p, None, lang) for p in qs]
        today = timezone.localdate().isoformat()
        mine = services.region_group(request.user.region)
        default = next(
            (e["id"] for e in events if e["date"][:10] == today and e["region"] in mine),
            next((e["id"] for e in events if e["date"][:10] == today), events[0]["id"] if events else None),
        )
        return Response({"events": events, "default": default})


class StaffCheckInView(_Staff):
    """
    POST /webapp/staff/checkin/  { project_id, qr } или { project_id, user_id }
    → { result: ok|already|not_found|bad_qr, auto_added, person, counts }
    Не записан — записывается автоматически (как и в боте).
    """

    def post(self, request):
        project = EcoProject.objects.filter(id=request.data.get("project_id")).first()
        if not project:
            return Response({"result": "no_event"}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get("user_id"):
            volunteer = TGUser.objects.filter(id=request.data["user_id"]).first()
        else:
            tg_id = services.parse_qr(request.data.get("qr", ""))
            if not tg_id:
                return Response({"result": "bad_qr"})
            volunteer = TGUser.objects.filter(tg_id=tg_id).first()
        if not volunteer:
            return Response({"result": "not_found"})

        result, auto_added = services.check_in(volunteer, project)
        volunteer.refresh_from_db(fields=['balance'])

        if result == "ok" and volunteer.tg_id:
            v_lang = lang_of_sync(volunteer.tg_id)
            send_in_background([(volunteer.tg_id, bot_t(
                "attended_notify", v_lang, project=escape(project.title), balance=volunteer.balance,
            ))])

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
