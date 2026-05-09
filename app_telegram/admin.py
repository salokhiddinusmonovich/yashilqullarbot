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
    
    # ТВОЯ ЛОГИКА ОТОБРАЖЕНИЯ + ДОБАВИЛ ПРОЕКТ
    list_display = ('display_face', 'get_fullname', 'get_project_title', 'status', 'applied_at')
    
    # ФИЛЬТРАЦИЯ: Теперь ты можешь выбрать проект справа!
    list_filter = (('project', admin.RelatedOnlyFieldListFilter), 'status', 'applied_at')
    
    search_fields = ('user__fullname', 'user__username', 'user__phone', 'project__title')
    list_per_page = 500 

    actions = ['approve_and_invite', 'make_attended_with_msg', 'make_rejected', 'send_reminder_to_unregistered']

    # --- ТВОЯ ЛОГИКА (10 БАЛЛОВ И УВЕДОМЛЕНИЯ) - НЕ ТРОГАЛ ---
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
                    f"Guruhga qo'shiling: {obj.project.chat_link}"
                )
                async_to_sync(send_notification)(obj.user.tg_id, text)
                count += 1
            else:
                self.message_user(request, f"Ошибка: У проекта '{obj.project.title}' нет ссылки!", messages.ERROR)
        self.message_user(request, f"Одобрено и отправлено сообщений: {count}")


    @admin.action(description='🔔 Пнуть тех, кто в Боте, но не в Проекте (по региону)')
    def send_reminder_to_unregistered(self, request, queryset):
        # 1. Берем проект из первой выделенной записи (или можно взять самый свежий активный)
        if not queryset.exists():
            return
        
        project = queryset.first().project 
        project_region = getattr(project, 'region', 'tashkent_s') # Регион проекта

        # 2. Находим ID тех, кто УЖЕ подал заявку на этот проект (чтобы не спамить им)
        registered_user_ids = ProjectParticipation.objects.filter(
            project=project
        ).values_list('user__id', flat=True)

        # 3. Находим юзеров, которые: 
        # а) Из того же региона б) Их нет в списке зарегистрированных
        from app_telegram.models import TGUser # Импортируй свою модель юзера
        potential_volunteers = TGUser.objects.filter(
            region=project_region
        ).exclude(id__in=registered_user_ids)

        count = 0
        for user in potential_volunteers:
            if user.tg_id:
                # ИНСТРУКЦИЯ ДЛЯ ЮЗЕРА
                text = (
                    f"👋 <b>Salom, {user.fullname}!</b>\n\n"
                    f"Siz botimizdan ro'yxatdan o'tgansiz, lekin hali <b>{project.title}</b> loyihasiga ariza topshirmabsiz! 😊\n\n"
                    f"<b>Qanday ro'yxatdan o'tish mumkin?</b>\n"
                    f"1️⃣ Pastdagi <b>«Tadbirlar»</b> tugmasini bosing.\n"
                    f"2️⃣ <b>«Kelgusi tadbirlar»</b> bo'limiga kiring.\n"
                    f"3️⃣ Loyihani tanlab, <b>«✅ Ro'yxatdan o'tish»</b> tugmasini bosing.\n\n"
                    f"Sizni kutib qolamiz! 🌱"
                )
                try:
                    async_to_sync(send_notification)(user.tg_id, text)
                    count += 1
                except Exception as e:
                    print(f"Ошибка отправки для {user.tg_id}: {e}")

        self.message_user(request, f"Напоминание отправлено {count} пользователям из региона {project_region}.")

    @admin.action(description='🌟 Пришёл на эвент (+10 баллов + Уведомление)')
    def make_attended_with_msg(self, request, queryset):
        success_count = 0
        error_count = 0
        
        for obj in queryset:
            try:
                if obj.status != 'attended':
                    # 1. Сначала меняем статус и сохраняем (начисляем баллы)
                    obj.status = 'attended'
                    obj.save() 
                    
                    # 2. Обновляем данные из базы, чтобы получить актуальный баланс
                    obj.user.refresh_from_db()
                    
                    # 3. Отправляем уведомление
                    if obj.user.tg_id:
                        text = (
                            f"🌟 <b>Rahmat!</b>\n\n"
                            f"Siz bugungi loyihada faol qatnashdingiz va <b>10 eko-ball</b> oldingiz!\n"
                            f"Hozirgi balansingiz: <b>{obj.user.balance}</b> ball.\n\n"
                            # f"<i>Yana bir oz yig'ing va sovg'alarga almashtiring!</i>"
                        )
                        # Используем async_to_sync правильно
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

# --- ОСТАЛЬНЫЕ РЕГИСТРАЦИИ (БЕЗ ИЗМЕНЕНИЙ) ---
@admin.register(TGUser)
class TGUserAdmin(admin.ModelAdmin):
    list_display = ('display_avatar', 'fullname', 'username', 'balance', 'rank', 'region')
    list_filter = ('region', 'balance')
    search_fields = ('fullname', 'username')

    def display_avatar(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="40" height="40" style="border-radius:50%;"/>', obj.photo.url)
        return "—"
    display_avatar.short_description = "Avatar"

@admin.register(EcoProject)
class EcoProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location_name', 'is_active')
    list_filter = ('is_active', 'date')
    list_editable = ('is_active',)

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