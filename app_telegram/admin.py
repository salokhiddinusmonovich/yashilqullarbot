from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field
from .models import TGUser, TeamMemberYashilQullar, ProjectParticipation, EcoProject, Partner

# --- 1. Ресурс для Экспорта (Excel) ---
class ParticipationResource(resources.ModelResource):
    username = Field(attribute='user__username', column_name='Telegram Username')
    fullname = Field(attribute='user__fullname', column_name='F.I.SH (Имя)')
    phone = Field(attribute='user__phone', column_name='Telefon')
    experience = Field(attribute='user__experience', column_name='Tajriba (Опыт)')
    
    # Мы объявляем виртуальное поле для ссылки
    photo_url = Field(column_name='ССЫЛКА НА ФОТО (URL)')

    class Meta:
        model = ProjectParticipation
        fields = ('username', 'fullname', 'phone', 'experience', 'photo_url', 'project__title', 'status')
        export_order = fields

    # ВАЖНО: Название метода должно быть dehydrate_ + название поля выше
    def dehydrate_photo_url(self, obj):
        if obj.user and obj.user.photo:
            # Твой домен (поменяй на свой IP или домен сервера)
            domain = "http://127.0.0.1:8000" 
            return f"{domain}{obj.user.photo.url}"
        return "Нет фото"

# --- 2. Настройка Админки ---
@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipationResource
    
    # В админке показываем фоточку и основные данные
    list_display = ('display_face', 'get_username', 'get_fullname', 'project', 'status')
    list_filter = ('project', 'status')
    search_fields = ('user__fullname', 'user__username', 'user__phone')

    # ФОТО В ТАБЛИЦЕ АДМИНКИ (Лицо)
    def display_face(self, obj):
        if obj.user and obj.user.photo:
            return format_html('<img src="{}" width="60" height="60" style="border-radius:10px; object-fit:cover;"/>', obj.user.photo.url)
        return "Нет фото"
    display_face.short_description = 'Лицо'

    # Получаем юзернейм
    def get_username(self, obj):
        return f"@{obj.user.username}" if obj.user.username else f"ID: {obj.user.tg_id}"
    get_username.short_description = 'Username'

    # Получаем ФИО
    def get_fullname(self, obj):
        return obj.user.fullname
    get_fullname.short_description = 'Имя'

# --- 3. Остальные регистрации ---
@admin.register(TGUser)
class TGUserAdmin(admin.ModelAdmin):
    list_display = ('tg_id', 'username', 'fullname', 'phone')

admin.site.register(EcoProject)
admin.site.register(TeamMemberYashilQullar)

admin.site.register(Partner)