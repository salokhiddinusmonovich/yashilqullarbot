from django.contrib import admin
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field
from .models import TGUser, TeamMemberYashilQullar, ProjectParticipation, EcoProject, Partner

# --- 1. РЕСУРС ДЛЯ ЭКСПОРТА ---
class ParticipationResource(resources.ModelResource):
    username = Field(attribute='user__username', column_name='Telegram Username')
    fullname = Field(attribute='user__fullname', column_name='F.I.SH (Имя)')
    phone = Field(attribute='user__phone', column_name='Telefon')
    project_name = Field(attribute='project__title', column_name='Loyiha nomi') # Фильтр в экспорте

    class Meta:
        model = ProjectParticipation
        fields = ('username', 'fullname', 'phone', 'project_name', 'status')
        export_order = fields

# --- 2. ACTIONS (МАССОВЫЕ ДЕЙСТВИЯ) ---
@admin.action(description='✅ Отметить как ПРИШЕДШИХ (+10 баллов)')
def make_attended(modeladmin, request, queryset):
    for obj in queryset:
        if obj.status != 'attended':
            obj.status = 'attended'
            obj.save() # Начисляет баллы автоматически

@admin.action(description='❌ Отменить участие (Удалить баллы)')
def make_rejected(modeladmin, request, queryset):
    for obj in queryset:
        obj.status = 'rejected'
        obj.save()

# --- 3. ГЛАВНАЯ АДМИНКА С ФИЛЬТРАЦИЕЙ ПО ЭВЕНТУ ---
@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipationResource
    
    # 1. Порядок в таблице
    list_display = ('display_face', 'get_fullname', 'project', 'status', 'applied_at')
    
    list_filter = (
        ('project', admin.RelatedOnlyFieldListFilter), # Это заставит фильтр появиться
        'status', 
        'applied_at'
    )
    
    # 3. Поиск и действия
    search_fields = ('user__fullname', 'user__username', 'user__phone')
    actions = [make_attended, make_rejected]
    list_per_page = 500 

    def display_face(self, obj):
        if obj.user and obj.user.photo:
            try:
                # Проверяем, есть ли url у фото
                url = obj.user.photo.url
                return format_html(
                    '<img src="{}" width="65" height="65" style="border-radius:10px; object-fit:cover; border:2px solid #555;"/>', 
                    url
                )
            except Exception:
                return format_html('<b style="color:red;">Ошибка пути</b>')
        return "Нет фото"
    display_face.short_description = 'ЛИЦО'

    def get_fullname(self, obj):
        return obj.user.fullname
    get_fullname.short_description = 'F.I.SH'

# --- 4. ОСТАЛЬНЫЕ РЕГИСТРАЦИИ ---

@admin.register(TGUser)
class TGUserAdmin(admin.ModelAdmin):
    list_display = ('fullname', 'username', 'balance', 'rank', 'region')
    list_filter = ('region', 'balance')
    search_fields = ('fullname', 'username')

@admin.register(EcoProject)
class EcoProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location_name', 'is_active')
    list_filter = ('is_active', 'date')

admin.site.register(Partner)
admin.site.register(TeamMemberYashilQullar)