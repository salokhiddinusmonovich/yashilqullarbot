from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse # Добавь этот импорт

# Создадим быструю функцию для главной страницы
def home_view(request):
    return HttpResponse("<h1>Salokhiddin, Django is working!</h1><p>Go to <a href='/admin/'>/admin/</a> to login.</p>")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view), # Добавь этот путь для главной страницы
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)