from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse # Добавь этот импорт
from django.urls import re_path
from django.views.static import serve

# Создадим быструю функцию для главной страницы
def home_view(request):
    return HttpResponse("<h1>Salokhiddin, Django is working!</h1><p>Go to <a href='/admin/'>/admin/</a> to login.</p>")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view), # Добавь этот путь для главной страницы
]
# Добавляем это принудительно для медиа:
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]