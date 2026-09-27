from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.shortcuts import render
from django.urls import path, include, re_path
from django.utils import translation
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

HOME_TEXTS = {
    "uz": {
        "pill": "Ekologik volontyorlik harakati", "title_1": "Birgalikda", "title_2": "tabiatni asraymiz",
        "lead": "Yashil Qo'llar — yoshlarni ekologik tadbirlarga birlashtiruvchi jamoa. Botda ro'yxatdan o'ting, "
                "tadbirga yoziling, QR-kodingizni ko'rsating va sertifikat oling.",
        "btn_bot": "Botni ochish", "st_users": "volontyorlar", "st_events": "tadbirlar",
        "st_checkins": "tasdiqlangan qatnashuvlar", "st_regions": "hudud",
        "l_admin": "Admin panel", "l_admin_d": "Tadbirlar, qatnashchilar, statistika va Excel.",
        "l_api": "API hujjatlari", "l_api_d": "Sayt va Mini App uchun REST API.",
        "l_bot": "Telegram bot", "l_bot_d": "Ro'yxatdan o'tish, tadbirlar va shaxsiy QR-kod.",
        "footer": "barqaror kelajak sari",
    },
    "ru": {
        "pill": "Экологическое волонтёрское движение", "title_1": "Вместе", "title_2": "бережём природу",
        "lead": "Yashil Qo'llar — команда, которая объединяет молодёжь вокруг эко-мероприятий. Зарегистрируйтесь в боте, "
                "запишитесь на мероприятие, покажите QR-код и получите сертификат.",
        "btn_bot": "Открыть бота", "st_users": "волонтёров", "st_events": "мероприятий",
        "st_checkins": "подтверждённых участий", "st_regions": "регионов",
        "l_admin": "Админ-панель", "l_admin_d": "Мероприятия, участники, статистика и Excel.",
        "l_api": "Документация API", "l_api_d": "REST API для сайта и Mini App.",
        "l_bot": "Telegram-бот", "l_bot_d": "Регистрация, мероприятия и личный QR-код.",
        "footer": "к устойчивому будущему",
    },
    "en": {
        "pill": "Eco volunteering movement", "title_1": "Together we", "title_2": "protect nature",
        "lead": "Yashil Qo'llar brings young people together around eco events. Sign up in the bot, "
                "register for an event, show your QR code and get a certificate.",
        "btn_bot": "Open the bot", "st_users": "volunteers", "st_events": "events",
        "st_checkins": "confirmed check-ins", "st_regions": "regions",
        "l_admin": "Admin panel", "l_admin_d": "Events, participants, statistics and Excel.",
        "l_api": "API docs", "l_api_d": "REST API for the website and Mini App.",
        "l_bot": "Telegram bot", "l_bot_d": "Sign-up, events and your personal QR code.",
        "footer": "towards a sustainable future",
    },
}


def _home_stats():
    stats = cache.get("yq_home_stats")
    if stats is None:
        from django.db.models import Count
        from app_telegram.models import TGUser, EcoProject, ProjectParticipation
        stats = {
            "users": TGUser.objects.count(),
            "events": EcoProject.objects.count(),
            "checkins": ProjectParticipation.objects.filter(status="attended").count(),
            "regions": TGUser.objects.exclude(region__isnull=True).exclude(region="")
                       .values("region").annotate(n=Count("id")).count(),
        }
        cache.set("yq_home_stats", stats, 300)
    return stats


def home_view(request):
    lang = request.GET.get("lang") or (translation.get_language() or "ru")[:2]
    if lang not in HOME_TEXTS:
        lang = "ru"
    response = render(request, "home.html", {
        "lang": lang,
        "tx": HOME_TEXTS[lang],
        "stats": _home_stats(),
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
    })
    if "lang" in request.GET:
        # запоминаем выбор — админка откроется на том же языке
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang, max_age=365 * 24 * 3600)
    return response


from app_telegram.views_cert import certificate_file, certificate_verify, cv_file, wrapped_image

urlpatterns = [
    # 🎓 сертификат участника: /c/<id>-<подпись>.pdf|jpg
    path('c/<int:pid>-<str:sig>.<str:ext>', certificate_file, name='certificate-file'),
    path('c/cv/<int:uid>-<str:sig>.pdf', cv_file, name='cv-file'),
    path('c/v/<int:pid>-<str:sig>', certificate_verify, name='certificate-verify'),
    path('c/w/<int:uid>-<int:year>-<str:sig>.jpg', wrapped_image, name='wrapped-image'),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # переключатель языка в админке
    path('', home_view),
    path('', include('API.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
