import asyncio
from django.contrib import admin, messages
from django.utils.html import format_html
from aiogram import Bot
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field
from asgiref.sync import async_to_sync # asyncio.run ўрнига хавфсизроқ

from .models import (
    TGUser, TeamMemberYashilQullar, ProjectParticipation, 
    EcoProject, Partner
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
    actions = ['approve_and_invite', 'make_attended_with_msg', 'make_rejected']

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

    # --- ТВОИ ACTIONS (approve_and_invite и т.д. без изменений) ---
    @admin.action(description='✅ Одобрить и отправить ССЫЛКУ НА ЧАТ')
    def approve_and_invite(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.project.chat_link:
                obj.status = 'approved'
                obj.save()
                
                text = (
                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                    f"Siz <b>{obj.project.title}</b> loyihasiga qabul qilindingiz!\n"
                    f"Guruhga qo'shiling: " 
                    f"{obj.project.chat_link}"
                )
                async_to_sync(send_notification)(obj.user.tg_id, text)
                count += 1
            else:
                self.message_user(request, f"Ошибка: У проекта '{obj.project.title}' нет ссылки!", messages.ERROR)
        self.message_user(request, f"Одобрено и отправлено сообщений: {count}")

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
    # ДОБАВЛЯЕМ 'is_admin' и 'is_tester' СЮДА:
    list_display = ('display_name', 'tg_id', 'region', 'balance', 'colored_status', 'is_admin', 'is_tester')
    
    # Теперь list_editable будет работать без ошибок
    list_editable = ('is_admin', 'is_tester')
    
    list_filter = ('is_admin', 'is_tester', 'region')
    search_fields = ('fullname', 'tg_id', 'phone', 'username')

    # Остальной код (display_name, colored_status, fieldsets) оставляешь без изменений
    def display_name(self, obj):
        if obj.is_admin:
            return format_html('<strong style="color: #d9534f;">⭐ [ADMIN] {}</strong>', obj.fullname)
        if obj.is_tester:
            return format_html('<span style="color: #5bc0de;">🧪 {}</span>', obj.fullname)
        return obj.fullname
    display_name.short_description = 'ФИО пользователя'

    def colored_status(self, obj):
        rank = obj.rank
        color = "#5cb85c" if obj.balance >= 150 else "#f0ad4e"
        if obj.balance < 50:
            color = "#777"
        return format_html('<b style="color: {};">{}</b>', color, rank)
    colored_status.short_description = 'Статус / Ранг'

    fieldsets = (
        ('Личные данные', {'fields': ('fullname', 'photo', 'age', 'phone', 'email', 'education_place', 'region')}),
        ('Технические данные', {'fields': ('tg_id', 'username', 'experience')}),
        ('Статус и Бонусы', {'fields': ('is_admin', 'is_tester', 'balance')}),
    )

@admin.register(EcoProject)
class EcoProjectAdmin(admin.ModelAdmin):
    search_fields = ('title',)
    list_display = ('title', 'date', 'location_name', 'is_active')
    list_filter = ('is_active', 'date')
    list_editable = ('is_active',)

    actions = ['remind_local_users']

    @admin.action(description='🔔 Рассылка: "Вы забыли зарегистрироваться" (Ташкент + Область)')
    def remind_local_users(self, request, queryset):
        # Список кодов регионов, которые мы считаем "Ташкентом"
        # Убедитесь, что эти строки совпадают с теми, что записаны у вас в базе (напр. 'tashkent_c', 'tashkent_s')
        tashkent_group = ['tashkent_v', 'tashkent_s'] 

        for project in queryset:
            project_region = getattr(project, 'region', 'tashkent_s')

            # 1. Определяем, кого искать
            if project_region in tashkent_group:
                # Если проект в Ташкенте, ищем пользователей и из города, и из области
                target_regions = tashkent_group
            else:
                # Если проект в другом регионе (напр. Самарканд), ищем только там
                target_regions = [project_region]

            # 2. Находим тех, кто уже зарегистрирован
            registered_ids = ProjectParticipation.objects.filter(
                project=project
            ).values_list('user__id', flat=True)

            # 3. Фильтруем пользователей:
            # region__in — это поиск по списку (если регион входит в список target_regions)
            unregistered_users = TGUser.objects.filter(
                region__in=target_regions
            ).exclude(id__in=registered_ids)

            count = 0
            for user in unregistered_users:
                if user.tg_id:
                    text = (
                        f"👋 Salom, {user.fullname}!\n\n"
                        f"Toshkent va Toshkent viloyati bo'ylab {project.title} loyihasi rejalashtirilgan! ✨\n"
                        f"Lekin siz hali ro'yxatdan o'tmabsiz. Safimizga qo'shiling! 👇\n\n"
                        f"Qanday ro'yxatdan o'tish mumkin?\n"
                        f"1️⃣ Bot menyusidan «Tadbirlar» bo'limiga kiring.\n"
                        f"2️⃣ «Kelgusi tadbirlar» tugmasini bosing.\n"
                        f"3️⃣ Loyihani tanlang va «✅ Ro'yxatdan o'tish» tugmasini bosing.\n\n"
                        f"Sizni kutib qolamiz! 🌿"
                    )
                    try:
                        async_to_sync(send_notification)(user.tg_id, text)
                        count += 1
                    except Exception as e:
                        print(f"Ошибка отправки {user.tg_id}: {e}")

            self.message_user(
                request, 
                f"Проект '{project.title}': отправлено {count} уведомлений для региона(ов) {target_regions}."
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

admin.site.register(Partner)