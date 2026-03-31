from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field
from .models import TGUser, TeamMemberYashilQullar, ProjectParticipation, EcoProject, Partner

# --- 1. РЕСУРС ДЛЯ ЭКСПОРТА (EXCEL) ---
class ParticipationResource(resources.ModelResource):
    username = Field(attribute='user__username', column_name='Telegram Username')
    fullname = Field(attribute='user__fullname', column_name='F.I.SH (Имя)')
    phone = Field(attribute='user__phone', column_name='Telefon')
    experience = Field(attribute='user__experience', column_name='Tajriba (Опыт)')
    photo_url = Field(column_name='ССЫЛКА НА ФОТО (URL)')

    class Meta:
        model = ProjectParticipation
        fields = ('username', 'fullname', 'phone', 'experience', 'photo_url', 'project__title', 'status')
        export_order = fields

    def dehydrate_photo_url(self, obj):
        if obj.user and obj.user.photo:
            # Твой IP сервера для ссылок в Excel
            domain = "http://127.0.0.1:8000" 
            return f"{domain}{obj.user.photo.url}"
        return "Нет фото"

# --- 2. МАССОВЫЕ ДЕЙСТВИЯ (ACTIONS) ---

@admin.action(description='✅ Отметить как ПРИШЕДШИХ (+10 баллов)')
def make_attended(modeladmin, request, queryset):
    for obj in queryset:
        if obj.status != 'attended':
            obj.status = 'attended'
            obj.save() # Наша модель сама начислит баллы через свой метод save()

@admin.action(description='❌ Отменить участие (Удалить баллы)')
def make_rejected(modeladmin, request, queryset):
    for obj in queryset:
        obj.status = 'rejected'
        obj.save()

# --- 3. НАСТРОЙКА АДМИНКИ УЧАСТНИКОВ ---
@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipationResource
    
    # В админке показываем фоточку и основные данные
    list_display = ('display_face', 'get_fullname', 'get_username', 'project', 'status', 'applied_at')
    
    # Фильтры — ТВОЁ СПАСЕНИЕ для 300+ юзеров
    list_filter = ('project', 'status', 'applied_at')
    
    # Поиск по всем полям
    search_fields = ('user__fullname', 'user__username', 'user__phone')
    
    # Добавляем Кнопки Массового Действия
    actions = [make_attended, make_rejected]

    # ФОТО В ТАБЛИЦЕ АДМИНКИ (Лицо)
    def display_face(self, obj):
        if obj.user and obj.user.photo:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:50%; object-fit:cover;"/>', obj.user.photo.url)
        return "Нет фото"
    display_face.short_description = 'Лицо'

    def get_username(self, obj):
        return f"@{obj.user.username}" if obj.user.username else f"ID: {obj.user.tg_id}"
    get_username.short_description = 'Username'

    def get_fullname(self, obj):
        return obj.user.fullname
    get_fullname.short_description = 'Имя'

# --- 4. ОСТАЛЬНЫЕ МОДЕЛИ ---

@admin.register(TGUser)
class TGUserAdmin(admin.ModelAdmin):
    list_display = ('display_avatar', 'fullname', 'username', 'balance', 'rank', 'region')
    list_filter = ('region', 'balance')
    search_fields = ('fullname', 'username', 'phone')

    def display_avatar(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="40" height="40" style="border-radius:20px;"/>', obj.photo.url)
        return "👤"
    display_avatar.short_description = 'Фото'

@admin.register(EcoProject)
class EcoProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location_name', 'is_active')

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')

@admin.register(TeamMemberYashilQullar)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'focus')
    def get_name(self, obj):
        return obj.tg_user.fullname