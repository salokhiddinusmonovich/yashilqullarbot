import asyncio
import logging
from datetime import timedelta
from html import escape
from pathlib import Path

from aiogram import Bot
from asgiref.sync import async_to_sync
from django.conf import settings
from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field
from modeltranslation.admin import TranslationAdmin

from tgbot.i18n import t as bot_t, role_label
from tgbot.services.lang import lang_of_sync, langs_of_sync
from .i18n import tr, trn
from .telegram import send_in_background
from .models import (
    TGUser, TeamMemberYashilQullar, ProjectParticipation, ProjectNotification,
    EcoProject, EcoProjectImage, Partner,
    Article, Tag, Comment, LoginToken, EventFeedback, ArticleImage,
)

logger = logging.getLogger(__name__)

# Токен один на весь проект — из settings.py (тот же BOT_TOKEN из .env,
# что и у самого бота), иначе после перевыпуска токена уведомления
# отсюда молча падали бы с 401.
BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN

# Гифка к поздравлению с ролью — необязательна: нет файла → просто текст.
ROLE_PROMOTION_GIF = Path(__file__).resolve().parent.parent / "tgbot" / "assets" / "role_promotion.gif"


# ─────────────────────────── отправка в Telegram ───────────────────────────

async def send_role_promotion_notification(user_id, text):
    # Без try/except: ошибка должна долететь до save_model(), чтобы админ
    # увидел РЕАЛЬНУЮ причину ("бот заблокирован" и т.п.), а не ложное "✅".
    bot = Bot(token=BOT_TOKEN)
    try:
        if ROLE_PROMOTION_GIF.exists():
            with open(ROLE_PROMOTION_GIF, 'rb') as gif:
                await bot.send_animation(user_id, gif, caption=text, parse_mode="HTML")
        else:
            await bot.send_message(user_id, text, parse_mode="HTML")
    finally:
        await (await bot.get_session()).close()


def _badge(text, color, bg=None):
    return format_html(
        '<span class="yq-badge" style="--c:{};--bg:{}">{}</span>', color, bg or f"{color}1f", text,
    )


# ─────────────────────────── участники ───────────────────────────

class ParticipationResource(resources.ModelResource):
    username = Field(attribute='user__username', column_name='Telegram Username')
    fullname = Field(attribute='user__fullname', column_name='F.I.SH (Имя)')
    phone = Field(attribute='user__phone', column_name='Telefon')
    experience = Field(attribute='user__experience', column_name='Tajribasi (Опыт)')
    photo_url = Field(column_name='Rasm (Ссылка на фото)')
    project_name = Field(attribute='project__title', column_name='Loyiha nomi')

    class Meta:
        model = ProjectParticipation
        fields = ('username', 'fullname', 'phone', 'experience', 'photo_url', 'project_name', 'status')
        export_order = fields

    def get_queryset(self):
        return super().get_queryset().select_related('user', 'project')

    def dehydrate_photo_url(self, obj):
        if obj.user and obj.user.photo:
            server_url = "http://173.249.19.32:8000"
            return f"{server_url}{obj.user.photo.url}"
        return "—"


STATUS_COLORS = {'pending': '#d97706', 'approved': '#0284c7', 'attended': '#16a34a', 'rejected': '#dc2626'}


class MoveActionForm(ActionForm):
    """Поле рядом с выпадающим списком действий — для «перенести на другое мероприятие»."""
    target_project = forms.ModelChoiceField(
        queryset=EcoProject.objects.order_by('-date'), required=False, label=tr('move_target'),
    )


@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipationResource
    action_form = MoveActionForm
    # кнопка «📋 Отчёт: кто пришёл» над списком (рядом с «Экспорт»)
    change_list_template = "admin/app_telegram/projectparticipation/change_list.html"

    def get_urls(self):
        from django.urls import path
        return [
            path('report/', self.admin_site.admin_view(self.report_view), name='app_telegram_projectparticipation_report'),
            path('certificate/', self.admin_site.admin_view(self.certificate_view), name='app_telegram_projectparticipation_certificate'),
            path('assistant/', self.admin_site.admin_view(self.assistant_view), name='app_telegram_projectparticipation_assistant'),
        ] + super().get_urls()

    def certificate_view(self, request):
        """🎓 Дизайны сертификатов: сезоны (🍂❄️🌸☀️) и свои; PNG из Canva, месяцы, координаты, живой предпросмотр."""
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse, HttpResponseRedirect
        from django.template.response import TemplateResponse
        from . import certificates as C

        if not request.user.is_superuser and not self.has_change_permission(request):
            raise PermissionDenied
        all_designs = C.designs()
        slugs = [d["slug"] for d in all_designs]
        slug = request.GET.get("d") or request.POST.get("d") or C.FALLBACK
        if slug not in slugs:
            slug = C.FALLBACK
        here = f"{request.path}?d={slug}"
        lay = C.layout(slug)

        if request.GET.get("preview"):
            q = dict(lay)
            for k, v in C.DEFAULT_LAYOUT.items():
                if k in request.GET:
                    try:
                        q[k] = (request.GET[k] in ("1", "true", "on")) if isinstance(v, bool) else type(v)(request.GET[k])
                    except ValueError:
                        pass
            img = C.render("Muhammadaziz Khabibullayev", timezone.localdate().strftime("%d.%m.%Y"), "YQ-001043", q,
                           slug=slug, event_title="Daraxt ekish — Yunusobod")
            return HttpResponse(C.to_jpg(img, max_w=1200), content_type="image/jpeg")

        if request.method == "POST":
            act = request.POST.get("act")
            if act == "announce":
                self._announce_past(request)
                return HttpResponseRedirect(here)
            if act == "new":
                new = C.create_design(request.POST.get("name", "").strip(), request.POST.get("emoji", "").strip() or "🎨")
                return HttpResponseRedirect(f"{request.path}?d={new}")
            if act == "reset":
                C.delete_design(slug)
                self.message_user(request, trn("cert_reset_done"))
                return HttpResponseRedirect(request.path if slug not in C.SEASONS else here)
            f = request.FILES.get("template")
            if f:
                try:
                    C.save_template(f, slug)
                except Exception:
                    self.message_user(request, trn("cert_bad_file"), messages.ERROR)
                    return HttpResponseRedirect(here)
            data = {k: request.POST.get(k) for k in C.DEFAULT_LAYOUT
                    if not isinstance(C.DEFAULT_LAYOUT[k], bool) and request.POST.get(k) not in (None, "")}
            data["show_number"] = bool(request.POST.get("show_number"))
            data["event_show"] = bool(request.POST.get("event_show"))
            data["body_show"] = bool(request.POST.get("body_show"))
            try:
                C.save_layout(data, slug)
            except ValueError:
                pass
            import re as _re
            events = [int(x) for x in _re.findall(r"\d+", request.POST.get("events", ""))]
            C.save_meta(slug, months=request.POST.getlist("months"), events=events)
            self.message_user(request, trn("cert_saved"))
            return HttpResponseRedirect(here)

        labels = {"x": trn("cert_x"), "y": trn("cert_y"), "size": trn("cert_size"), "color": trn("cert_color"), "max_w": trn("cert_maxw")}
        groups = []
        labels.update({"line": trn("cert_line"), "lines": trn("cert_lines"), "text": trn("cert_body_text")})
        for title, prefix in ((trn("cert_name"), "name_"), (trn("cert_date"), "date_"), (trn("cert_number"), "number_"),
                              (trn("cert_body"), "body_"), (trn("cert_event"), "event_")):
            fs = [(k, labels.get(k.split("_", 1)[1], k), lay[k],
                   "color" if k.endswith("color") else "textarea" if isinstance(v, str) else "number")
                  for k, v in C.DEFAULT_LAYOUT.items() if k.startswith(prefix) and not isinstance(v, bool)]
            groups.append((title, prefix, fs))
        cur = next(d for d in all_designs if d["slug"] == slug)
        month_names = ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"]
        ctx = {
            **self.admin_site.each_context(request), "title": trn("cert_title"), "opts": self.model._meta,
            "designs": all_designs, "cur": cur, "slug": slug, "groups": groups,
            "show_number": lay.get("show_number"), "event_show": lay.get("event_show"), "body_show": lay.get("body_show"),
            "months": [(i + 1, n, (i + 1) in cur.get("months", [])) for i, n in enumerate(month_names)],
            "events_text": ", ".join(str(x) for x in cur.get("events", [])),
            "recent_events": list(EcoProject.objects.order_by('-date').values('id', 'title', 'date')[:12]),
        }
        return TemplateResponse(request, "admin/yq_certificate.html", ctx)

    def assistant_view(self, request):
        """🤖 Что знает ИИ-помощник: свои заметки (media/assistant/extra.txt) + то, что берётся из базы."""
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponseRedirect
        from django.template.response import TemplateResponse
        from tgbot.services import ai

        if not request.user.is_superuser and not self.has_change_permission(request):
            raise PermissionDenied
        path = ai.extra_path()
        if request.method == "POST":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text((request.POST.get("extra") or "").strip()[:6000], encoding="utf-8")
            self.message_user(request, trn("ai_saved"))
            return HttpResponseRedirect(request.path)
        try:
            extra = path.read_text(encoding="utf-8")
        except OSError:
            extra = ""
        ctx = {**self.admin_site.each_context(request), "title": trn("ai_title"), "opts": self.model._meta,
               "extra": extra, "info": ai._project_info_sync(), "enabled": ai.enabled()}
        return TemplateResponse(request, "admin/yq_assistant.html", ctx)

    def _announce_past(self, request):
        from tgbot.services.lang import _sclient
        try:
            if not _sclient().set("cert:announced", 1, nx=True):
                self.message_user(request, trn("cert_announce_already"), messages.WARNING)
                return
        except Exception:
            pass
        rows = (ProjectParticipation.objects.filter(status='attended', user__tg_id__isnull=False)
                .values_list('user__tg_id').annotate(n=Count('id')))
        rows = list(rows)
        langs = langs_of_sync([tg for tg, _ in rows])
        send_in_background([(tg, bot_t("cert_past", langs.get(tg), n=n)) for tg, n in rows])
        self.message_user(request, trn("cert_announce_done", n=len(rows)))


    def report_view(self, request):
        """Отчёт «кто пришёл»: период + регион → таблица на странице и Excel (app_telegram/reports.py)."""
        from django.core.exceptions import PermissionDenied
        from django.http import HttpResponse
        from django.template.response import TemplateResponse
        from django.utils.dateparse import parse_date
        from django.utils.translation import get_language
        from tgbot.i18n import t as bt
        from . import reports

        if not self.has_view_permission(request):
            raise PermissionDenied
        lang = (get_language() or "ru")[:2]
        lang = lang if lang in ("uz", "ru", "en") else "ru"
        g = request.GET
        period = g.get("period", "today")
        region = g.get("region", "all")
        if region not in reports.REGION_CHOICES:
            region = "all"
        if period == "custom":
            d_from = parse_date(g.get("from") or "")
            d_to = parse_date(g.get("to") or "") or d_from
            d_from = d_from or d_to
            if d_from and d_to and d_from > d_to:
                d_from, d_to = d_to, d_from
        else:
            period = period if period in reports.PERIODS else "today"
            d_from, d_to = reports.period_range(period)
        regions = reports.region_codes(region)
        parts = reports.attendance(d_from, d_to, regions)
        events = reports.event_summary(d_from, d_to, regions)
        ptxt = reports.period_text(d_from, d_to, lang)
        rtxt = reports.region_choice_label(region, lang)

        if g.get("download"):
            title = f"{bt('rep_sheet_people', lang)} · {ptxt} · {rtxt}"
            buf = reports.build_xlsx(parts, events, lang, title, reports.no_shows(d_from, d_to, regions))
            resp = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            resp["Content-Disposition"] = f'attachment; filename="{reports.filename(d_from, d_to, region)}"'
            return resp

        q = request.GET.copy(); q["download"] = "1"
        ctx = {
            **self.admin_site.each_context(request),
            "title": trn("rep_title"), "opts": self.model._meta,
            "periods": [(p, bt(f"rep_p_{p}", lang)) for p in reports.PERIODS],
            "regions": [(r, reports.region_choice_label(r, lang)) for r in reports.REGION_CHOICES],
            "period": period, "region": region,
            "d_from": d_from.isoformat() if d_from else "", "d_to": d_to.isoformat() if d_to else "",
            "ptxt": ptxt, "rtxt": rtxt,
            "parts": parts[:100], "more": max(0, len(parts) - 100),
            "n_checkins": len(parts), "n_people": len({pp.user_id for pp in parts}),
            "events": events, "n_events": sum(1 for e in events if e.attended),
            "headers": bt("rep_people_headers", lang), "eheaders": bt("rep_event_headers", lang),
            "download_qs": q.urlencode(),
        }
        return TemplateResponse(request, "admin/yq_report.html", ctx)

    list_display = ('display_face', 'get_fullname', 'get_project_title', 'colored_status', 'applied_at')
    # регион волонтёра — чтобы быстро найти «самаркандцев на ташкентском мероприятии»
    list_filter = (('project', admin.RelatedOnlyFieldListFilter), 'status', 'user__region', 'applied_at')
    search_fields = ('user__fullname', 'user__username', 'user__phone', 'project__title')
    autocomplete_fields = ['user', 'project']
    actions = ['make_attended_with_msg', 'make_rejected', 'move_to_project']

    # СКОРОСТЬ: раньше 500 строк на страницу и без select_related —
    # это ~1000 отдельных SQL-запросов (юзер + проект на каждую строку)
    # и 500 фото за раз. Теперь 1 запрос и 100 строк.
    list_select_related = ('user', 'project')
    list_per_page = 100
    show_full_result_count = False
    ordering = ('-applied_at',)

    @admin.display(description=tr('f_status'), ordering='status')
    def colored_status(self, obj):
        return _badge(obj.get_status_display(), STATUS_COLORS.get(obj.status, '#64748b'))

    @admin.display(description=tr('project'), ordering='project__title')
    def get_project_title(self, obj):
        return obj.project.title

    @admin.display(description=tr('col_face'))
    def display_face(self, obj):
        if obj.user and obj.user.photo:
            try:
                return format_html(
                    '<img src="{}" width="44" height="44" loading="lazy" class="yq-avatar"/>', obj.user.photo.url
                )
            except Exception:
                pass
        initial = (obj.user.fullname or "?")[:1].upper() if obj.user else "?"
        return format_html('<span class="yq-avatar yq-avatar--empty">{}</span>', initial)

    @admin.display(description=tr('f_fullname'), ordering='user__fullname')
    def get_fullname(self, obj):
        return obj.user.fullname

    @admin.action(description=tr('act_attended'))
    def make_attended_with_msg(self, request, queryset):
        to_notify, already = [], 0
        for obj in queryset.select_related('user', 'project'):
            if obj.status == 'attended':
                already += 1
                continue
            obj.status = 'attended'
            obj.save()  # +10 баллов внутри ProjectParticipation.save()
            if obj.user.tg_id:
                to_notify.append(obj)

        langs = langs_of_sync([o.user.tg_id for o in to_notify])
        msgs = []
        for obj in to_notify:
            obj.user.refresh_from_db(fields=['balance'])
            lang = langs.get(obj.user.tg_id)
            msgs.append((obj.user.tg_id, bot_t(
                "attended_notify", lang, project=escape(obj.project.title), balance=obj.user.balance,
            )))
        if msgs:
            send_in_background(msgs)

        self.message_user(request, trn("msg_attended", n=len(to_notify)))
        if already:
            self.message_user(request, trn("msg_already", n=already), messages.WARNING)

    @admin.action(description=tr('act_move'))
    def move_to_project(self, request, queryset):
        from . import services
        target = None
        tid = request.POST.get('target_project')
        if tid:
            target = EcoProject.objects.filter(pk=tid).first()
        if not target:
            self.message_user(request, trn("msg_pick_target"), messages.ERROR)
            return
        moved = services.move_participations(queryset, target)
        attended = [u for u, was_attended in moved if was_attended and u.tg_id]
        langs = langs_of_sync([u.tg_id for u in attended])
        msgs = []
        for u in attended:
            u.refresh_from_db(fields=['balance'])
            msgs.append((u.tg_id, bot_t("attended_moved", langs.get(u.tg_id), project=escape(target.title), balance=u.balance)))
        if msgs:
            send_in_background(msgs)
        self.message_user(request, trn("msg_moved", n=len(moved), title=target.title))

    @admin.action(description=tr('act_rejected'))
    def make_rejected(self, request, queryset):
        n = 0
        for obj in queryset.select_related('user'):
            obj.status = 'rejected'
            obj.save()
            n += 1
        self.message_user(request, trn("msg_rejected", n=n))


# ─────────────────────────── пользователи ───────────────────────────

ROLE_COLORS = {
    'volunteer': '#64748b', 'coordinator': '#0891b2', 'main_coordinator': '#2563eb',
    'head_coordinator': '#7c3aed', 'mobilograph': '#ea580c', 'organizer': '#0d9488',
    'it': '#db2777', 'Founder': '#ca8a04',
}


@admin.register(TGUser)
class TGUserAdmin(admin.ModelAdmin):
    list_display = ('fullname', 'colored_role', 'region_badge', 'phone', 'balance', 'auth_provider', 'is_admin')
    list_filter = ('region', 'role', 'auth_provider', 'is_admin')
    search_fields = ('fullname', 'username', 'email', 'phone', 'tg_id')
    list_editable = ('is_admin',)
    list_per_page = 50
    show_full_result_count = False

    @admin.display(description=tr('f_role'), ordering='role')
    def colored_role(self, obj):
        color = ROLE_COLORS.get(obj.role, '#64748b')
        return format_html('<span class="yq-badge yq-badge--solid" style="--c:{}">{}</span>', color, obj.get_role_display())

    @admin.display(description=tr('f_region'), ordering='region')
    def region_badge(self, obj):
        if not obj.region:
            return format_html('<span style="color:var(--body-quiet-color)">—</span>')
        return _badge(obj.get_region_display(), '#16a34a')

    # Уведомление юзеру, когда админ меняет ему роль из карточки
    # (на его языке). На демоцию в волонтёры — не шлём.
    def save_model(self, request, obj, form, change):
        old_role = None
        if change and obj.pk:
            old_role = TGUser.objects.filter(pk=obj.pk).values_list('role', flat=True).first()

        super().save_model(request, obj, form, change)

        if change and obj.tg_id and old_role and old_role != obj.role and obj.role != TGUser.Role.VOLUNTEER:
            lang = lang_of_sync(obj.tg_id)
            text = bot_t("role_promo", lang, role=role_label(obj.role, lang))
            try:
                async_to_sync(send_role_promotion_notification)(obj.tg_id, text)
                self.message_user(request, trn("msg_role_sent", name=obj.fullname))
            except Exception as e:
                self.message_user(request, trn("msg_role_failed", e=e), messages.WARNING)


# ─────────────────────────── мероприятия ───────────────────────────

class EcoProjectImageInline(admin.TabularInline):
    model = EcoProjectImage
    extra = 1


@admin.register(EcoProject)
class EcoProjectAdmin(admin.ModelAdmin):
    search_fields = ('title',)
    list_display = ('title', 'date', 'region', 'location_name', 'registered', 'attended', 'has_group', 'is_active')
    list_filter = ('is_active', 'region', 'date')
    list_editable = ('is_active',)
    inlines = [EcoProjectImageInline]
    actions = ['remind_local_users', 'send_certificates_now']
    ordering = ('-date',)

    def get_queryset(self, request):
        # счётчики одним запросом, а не count() на каждую строку
        return super().get_queryset(request).annotate(
            _registered=Count('participants', filter=~Q(participants__status='rejected')),
            _attended=Count('participants', filter=Q(participants__status='attended')),
        )

    @admin.display(description=tr('col_registered'), ordering='_registered')
    def registered(self, obj):
        return f"{obj._registered} / {obj.max_participants}"

    @admin.display(description=tr('col_attended'), ordering='_attended')
    def attended(self, obj):
        return _badge(obj._attended, '#16a34a') if obj._attended else "0"

    @admin.display(description="👥", boolean=True)
    def has_group(self, obj):
        # без ссылки на группу волонтёры не узнают, где ждать сертификат
        return bool(obj.chat_link)

    @admin.action(description=tr('act_send_certs'))
    def send_certificates_now(self, request, queryset):
        from . import certificates as C
        from .telegram import send_documents_in_background
        pps = list(ProjectParticipation.objects.filter(project__in=queryset, status='attended', user__tg_id__isnull=False)
                   .values_list('id', 'user__tg_id', 'project__title', 'project_id'))
        langs = langs_of_sync([tg for _, tg, _, _ in pps])

        def build():
            out = []
            for pid, tg, title, _ in pps:
                pp = C.attended(pid)
                if pp:
                    out.append((tg, C.to_pdf(C.render_for(pp)), C.filename(pp),
                                bot_t("cert_caption", langs.get(tg), title=escape(title), number=C.number_of(pp))))
            return out

        def mark(delivered):
            from tgbot.services.lang import _sclient
            try:
                for _, tg, _, project_id in pps:
                    if tg in delivered:
                        _sclient().sadd(f"cert:sent:{project_id}", tg)
            except Exception:
                pass
        send_documents_in_background(build, on_done=mark)
        self.message_user(request, trn("msg_certs_sending", n=len(pps)))

    @admin.action(description=tr('act_remind'))
    def remind_local_users(self, request, queryset):
        tashkent_group = ['tashkent_v', 'tashkent_s']

        for project in queryset:
            region = getattr(project, 'region', 'tashkent_s')
            target_regions = tashkent_group if region in tashkent_group else [region]

            registered_ids = ProjectParticipation.objects.filter(project=project).values_list('user_id', flat=True)
            notified_ids = ProjectNotification.objects.filter(project=project).values_list('user_id', flat=True)
            users = list(
                TGUser.objects.filter(region__in=target_regions, tg_id__isnull=False)
                .exclude(id__in=registered_ids).exclude(id__in=notified_ids)
                .only('id', 'tg_id', 'fullname')
            )
            langs = langs_of_sync([u.tg_id for u in users])
            msgs = [
                (u.tg_id, bot_t("new_event_invite", langs.get(u.tg_id),
                                name=escape(u.fullname or ""), title=escape(project.title)))
                for u in users
            ]
            by_tg = {u.tg_id: u.id for u in users}

            def mark_notified(delivered, project_id=project.id, by_tg=by_tg):
                ProjectNotification.objects.bulk_create(
                    [ProjectNotification(project_id=project_id, user_id=by_tg[i]) for i in delivered],
                    ignore_conflicts=True,
                )

            if msgs:
                send_in_background(msgs, on_done=mark_notified)
            self.message_user(request, trn("msg_remind", title=project.title, n=len(msgs)))


@admin.register(TeamMemberYashilQullar)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('display_photo', 'fullname', 'focus', 'telegram_username')
    list_filter = ('focus',)
    search_fields = ('fullname', 'telegram_username')

    @admin.display(description=tr('f_photo'))
    def display_photo(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="44" height="44" loading="lazy" class="yq-avatar"/>', obj.photo.url)
        return "—"


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'stars', 'comment', 'created_at']
    list_filter = ['rating', ('project', admin.RelatedOnlyFieldListFilter)]
    readonly_fields = ['user', 'project', 'rating', 'comment', 'created_at']
    list_select_related = ('user', 'project')
    show_full_result_count = False

    @admin.display(description=tr('f_rating'), ordering='rating')
    def stars(self, obj):
        return "⭐" * obj.rating


class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 1


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'is_featured']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ArticleImageInline]
    autocomplete_fields = ['author']
    list_select_related = ('author',)


@admin.register(Tag)
class TagAdmin(TranslationAdmin):
    list_display = ('name', 'slug')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'article', 'text', 'created_at')
    list_select_related = ('user', 'article')
    # без raw_id форма рендерила <select> со ВСЕМИ юзерами и комментариями
    raw_id_fields = ('user', 'article', 'parent')
    show_full_result_count = False


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)


@admin.register(ProjectNotification)
class ProjectNotificationAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'sent_at')
    list_select_related = ('project', 'user')
    list_filter = (('project', admin.RelatedOnlyFieldListFilter),)
    raw_id_fields = ('project', 'user')
    show_full_result_count = False


@admin.register(LoginToken)
class LoginTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'status', 'tg_id', 'created_at')
    show_full_result_count = False


# ─────────────────────────── дашборд на главной админки ───────────────────────────

def dashboard_context():
    """Цифры для главной страницы админки. Кэш 60 сек — страница открывается мгновенно."""
    data = cache.get("yq_admin_dashboard")
    if data:
        return data

    now = timezone.now()
    today = timezone.localdate()
    upcoming = list(
        EcoProject.objects.filter(is_active=True, date__gte=now - timedelta(hours=12))
        .annotate(
            registered=Count('participants', filter=~Q(participants__status='rejected')),
            attended=Count('participants', filter=Q(participants__status='attended')),
        ).order_by('date')[:6]
    )
    for p in upcoming:
        p.fill = min(100, round(100 * p.registered / p.max_participants)) if p.max_participants else 0

    by_region = list(
        TGUser.objects.exclude(region__isnull=True).exclude(region='')
        .values('region').annotate(n=Count('id')).order_by('-n')[:8]
    )
    region_names = dict(TGUser.Region.choices)
    top = by_region[0]['n'] if by_region else 1
    for r in by_region:
        r['name'] = region_names.get(r['region'], r['region'])
        r['pct'] = round(100 * r['n'] / top)

    data = {
        "yq_stats": {
            "users": TGUser.objects.count(),
            "new_today": TGUser.objects.filter(created__date=today).count(),
            "new_week": TGUser.objects.filter(created__date__gte=today - timedelta(days=6)).count(),
            "active_events": EcoProject.objects.filter(is_active=True, date__gte=now).count(),
            "regs_today": ProjectParticipation.objects.filter(applied_at__date=today).count(),
            "attended_total": ProjectParticipation.objects.filter(status='attended').count(),
        },
        "yq_upcoming": upcoming,
        "yq_recent": list(
            ProjectParticipation.objects.select_related('user', 'project').order_by('-applied_at')[:8]
        ),
        "yq_regions": by_region,
    }
    cache.set("yq_admin_dashboard", data, 60)
    return data


_original_index = admin.site.index


def _index_with_dashboard(request, extra_context=None):
    extra_context = {**(extra_context or {}), **dashboard_context()}
    return _original_index(request, extra_context)


admin.site.index = _index_with_dashboard
admin.site.site_header = "Yashil Qo'llar"
admin.site.site_title = "Yashil Qo'llar"
admin.site.index_title = tr('dash_sub')
