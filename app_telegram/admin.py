import asyncio
from django.contrib import admin, messages
from django.utils.html import format_html
from aiogram import Bot
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field
from asgiref.sync import async_to_sync # asyncio.run ўрнига хавфсизроқ
from .models import ProjectNotification
import requests
from django.db.models import Q
from modeltranslation.admin import TranslationAdmin
from .models import (
    TGUser, TeamMemberYashilQullar, ProjectParticipation,
    EcoProject, EcoProjectImage, Partner,          # ← добавлен EcoProjectImage
    Article, Tag, Comment, LoginToken, EventFeedback, ArticleImage
)

BOT_TOKEN = "8597081931:AAHrLlthINCN8nIZp_zh3WEbzfc-5GhoHmw"

async def send_notification(user_id, text):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
    finally:
        await bot.close()

# --- 1. RESOURCE ---
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

    def dehydrate_photo_url(self, obj):
        if obj.user and obj.user.photo:
            server_url = "http://173.249.19.32:8000" 
            return f"{server_url}{obj.user.photo.url}"
        return "Нет фото"

# --- 2. ГЛАВНАЯ АДМИНКА УЧАСТНИКОВ ---
@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipationResource
    
    # Заменил 'status' на 'colored_status'
    list_display = ('display_face', 'get_fullname', 'get_project_title', 'colored_status', 'applied_at')
    
    list_filter = (('project', admin.RelatedOnlyFieldListFilter), 'status', 'applied_at')
    search_fields = ('user__fullname', 'user__username', 'user__phone', 'project__title')
    list_per_page = 500 
    autocomplete_fields = ['user', 'project']
    actions = ['make_attended_with_msg', 'make_rejected']

    # --- ФУНКЦИЯ ДЛЯ ЦВЕТНОГО СТАТУСА ---
    def colored_status(self, obj):
        colors = {
            'pending': '#ffc107',  # Желтый (Ожидание)
            'approved': '#17a2b8', # Бирюзовый (Одобрен)
            'attended': '#28a745', # Зеленый (Пришел)
            'rejected': '#dc3545', # Красный (Отказ)
        }
        color = colors.get(obj.status, '#6c757d') # Серый по умолчанию
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; '
            'border-radius: 20px; font-weight: bold; font-size: 11px; text-transform: uppercase;">'
            '{}</span>',
            color,
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'

   

    @admin.action(description='🌟 Пришёл на эвент (+10 баллов + Уведомление)')
    def make_attended_with_msg(self, request, queryset):
        success_count = 0
        error_count = 0
        for obj in queryset:
            try:
                if obj.status != 'attended':
                    obj.status = 'attended'
                    obj.save() 
                    obj.user.refresh_from_db()
                    if obj.user.tg_id:
                        text = (
                            f"🌟 <b>Rahmat!</b>\n\n"
                            f"Siz bugungi loyihada faol qatnashdingiz va <b>10 eko-ball</b> oldingiz!\n"
                            f"Hozirgi balansingiz: <b>{obj.user.balance}</b> ball.\n\n"
                        )
                        async_to_sync(send_notification)(obj.user.tg_id, text)
                        success_count += 1
                else:
                    self.message_user(request, f"Пользователь {obj.user.fullname} уже отмечен.", messages.WARNING)
            except Exception as e:
                error_count += 1
                self.message_user(request, f"Ошибка у {obj.user.fullname}: {str(e)}", messages.ERROR)
        self.message_user(request, f"Успешно: {success_count}. Ошибок: {error_count}")

    @admin.action(description='❌ Отменить участие (Удалить баллы)')
    def make_rejected(self, request, queryset):
        for obj in queryset:
            obj.status = 'rejected'
            obj.save()

    # --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
    def get_project_title(self, obj):
        return obj.project.title
    get_project_title.short_description = 'Loyiha nomi'

    def display_face(self, obj):
        if obj.user and obj.user.photo:
            try:
                return format_html(
                    '<img src="{}" width="65" height="65" style="border-radius:10px; object-fit:cover; border:2px solid #28a745;"/>', 
                    obj.user.photo.url
                )
            except:
                return "Ошибка пути"
        return "Нет фото"
    display_face.short_description = 'ЛИЦО'

    def get_fullname(self, obj):
        return obj.user.fullname
    get_fullname.short_description = 'F.I.SH'

@admin.register(TGUser)
class TGUserAdmin(admin.ModelAdmin):
    # ── Список — что видно в таблице ──
    list_display = (
        'fullname', 'colored_role', 'region_badge', 'phone', 'balance',
        'auth_provider', 'is_admin', 'created_at',
    )
 
    # ── ФИЛЬТРЫ СПРАВА — это то, что ты просил: клик по региону/роли
    # сразу фильтрует список, без ручного поиска ──
    list_filter = (
        'region',        # ← клик "Toshkent shahri" — видишь только их
        'role',          # ← клик "Coordinator" — видишь только координаторов
        'auth_provider', # telegram / email / google
        'is_admin',
    )
 
    # ── Поиск по имени/юзернейму/email/телефону ──
    search_fields = ('fullname', 'username', 'email', 'phone', 'tg_id')
 
    # ── Быстрая правка роли прямо из списка, без захода в карточку юзера ──
    list_editable = ('is_admin',) if 'is_admin' in list_display else ()
 
    # ── Пагинация — с ~1000 юзеров дефолтные 100/страница делают
    # страницу тяжёлой и медленной. 50 — комфортный компромисс. ──
    list_per_page = 50
 
    # ── Цвет по роли — тот же паттерн, что уже используется для
    # статусов участия в проектах (colored_status). ──
    def colored_role(self, obj):
        colors = {
            'volunteer': '#6c757d',       # серый — обычные волонтёры (их больше всего)
            'coordinator': '#17a2b8',     # бирюзовый
            'main_coordinator': '#0d6efd',# синий — выделяется среди координаторов
            'head_coordinator': '#6610f2',# фиолетовый
            'mobilograph': '#fd7e14',     # оранжевый
            'organizer': '#20c997',       # мятный
            'it': '#e83e8c',              # розовый
            'Founder': '#ffc107',         # жёлтый/золотой — основатели заметны сразу
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            'border-radius: 14px; font-weight: 700; font-size: 11px; white-space: nowrap;">{}</span>',
            color, obj.get_role_display(),
        )
    colored_role.short_description = 'Rol'
    colored_role.admin_order_field = 'role'  # позволяет сортировать по этой колонке
 
    # ── Регион тоже бейджем — проще визуально сканировать список ──
    def region_badge(self, obj):
        if not obj.region:
            return format_html('<span style="color:#999;">—</span>')
        return format_html(
            '<span style="background: rgba(34,197,94,0.12); color:#22c55e; padding: 3px 9px; '
            'border-radius: 10px; font-size: 11px; font-weight: 600;">{}</span>',
            obj.get_region_display(),
        )
    region_badge.short_description = 'Hudud'
    region_badge.admin_order_field = 'region'
 
class EcoProjectImageInline(admin.TabularInline):
    model = EcoProjectImage
    extra = 3
   

@admin.register(EcoProject)
class EcoProjectAdmin(admin.ModelAdmin):
    search_fields = ('title',)
    list_display = ('title', 'date', 'location_name', 'is_active', 'likes_count')
    list_filter = ('is_active', 'date')
    list_editable = ('is_active',)
    inlines = [EcoProjectImageInline]
 
    actions = ['remind_local_users']
 
    @admin.action(description='🔔 Рассылка: только новым юзерам')
    def remind_local_users(self, request, queryset):
        # ... (весь код действия остаётся без изменений, просто копия из твоего файла)
        tashkent_group = ['tashkent_v', 'tashkent_s']
 
        for project in queryset:
            project_region = getattr(project, 'region', 'tashkent_s')
 
            if project_region in tashkent_group:
                target_regions = tashkent_group
            else:
                target_regions = [project_region]
 
            registered_ids = ProjectParticipation.objects.filter(
                project=project
            ).values_list('user__id', flat=True)
 
            already_notified_ids = ProjectNotification.objects.filter(
                project=project
            ).values_list('user__id', flat=True)
 
            new_users = TGUser.objects.filter(
                region__in=target_regions
            ).exclude(id__in=registered_ids).exclude(id__in=already_notified_ids)
 
            count = 0
            for user in new_users:
                if user.tg_id:
                    text = (
                        f"👋 Salom, {user.fullname}!\n\n"
                        f"{project.title} loyihasi rejalashtirilgan! ✨\n"
                        f"Ro'yxatdan o'tish uchun botga kiring! 👇\n\n"
                        f"1️⃣ «Tadbirlar» bo'limiga kiring.\n"
                        f"2️⃣ «Kelgusi tadbirlar» tugmasini bosing.\n"
                        f"3️⃣ Loyihani tanlang va ro'yxatdan o'ting.\n\n"
                        f"Sizni kutib qolamiz! 🌿"
                    )
                    try:
                        async_to_sync(send_notification)(user.tg_id, text)
                        ProjectNotification.objects.get_or_create(
                            project=project, user=user
                        )
                        count += 1
                    except Exception as e:
                        print(f"Ошибка отправки {user.tg_id}: {e}")
 
            self.message_user(
                request,
                f"Проект '{project.title}': отправлено {count} новым юзерам."
            )

        


@admin.register(TeamMemberYashilQullar)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('display_photo', 'fullname', 'focus', 'telegram_username')
    list_filter = ('focus',)
    search_fields = ('fullname', 'telegram_username')

    def display_photo(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="border-radius:50%; object-fit:cover;"/>', obj.photo.url)
        return "Нет фото"
    display_photo.short_description = "Фото"


@admin.register(EventFeedback)
class EventFeedbackAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'rating', 'created_at']
    list_filter = ['rating', 'project']
    readonly_fields = ['user', 'project', 'rating', 'comment', 'created_at']

class ArticleImageInline(admin.TabularInline):
    model = ArticleImage
    extra = 3  # сразу 3 пустых слота под фото при создании поста



@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'is_featured']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ArticleImageInline]
    autocomplete_fields = ['author'] 

@admin.register(Tag)
class TagAdmin(TranslationAdmin): # Изменили здесь
    list_display = ('name', 'slug')
admin.site.register(Comment)
admin.site.register(Partner)
admin.site.register(ProjectNotification)
admin.site.register(LoginToken)




