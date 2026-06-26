from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse # Добавь этот импорт
from django.urls import re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Создадим быструю функцию для главной страницы
def home_view(request):
    return HttpResponse("<h1>Salokhiddin, Django is working!</h1><p>Go to <a href='/admin/'>/admin/</a> to login.</p>")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view), # Добавь этот путь для главной страницы
    path('', include('API.urs.py')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
# Добавляем это принудительно для медиа:
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]