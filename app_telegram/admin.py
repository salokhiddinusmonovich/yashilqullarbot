import asyncio
from django.contrib import admin, messages
from django.utils.html import format_html
from aiogram import Bot
from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field

from .models import (
    TGUser, TeamMemberYashilQullar, ProjectParticipation, 
    EcoProject, Partner
)

# --- НАСТРОЙКА БОТА ДЛЯ ОПОВЕЩЕНИЙ ---
# Вставь сюда свой токен
BOT_TOKEN = "8597081931:AAHrLlthINCN8nIZp_zh3WEbzfc-5GhoHmw"

async def send_notification(user_id, text):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
    finally:
        await bot.close()

# --- 1. РЕСУРС ДЛЯ ЭКСПОРТА ---
class ParticipationResource(resources.ModelResource):
    username = Field(attribute='user__username', column_name='Telegram Username')
    fullname = Field(attribute='user__fullname', column_name='F.I.SH (Имя)')
    phone = Field(attribute='user__phone', column_name='Telefon')
    project_name = Field(attribute='project__title', column_name='Loyiha nomi')

    class Meta:
        model = ProjectParticipation
        fields = ('username', 'fullname', 'phone', 'project_name', 'status')
        export_order = fields

# --- 2. ГЛАВНАЯ АДМИНКА УЧАСТНИКОВ ---
@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipationResource
    list_display = ('display_face', 'get_fullname', 'project', 'status', 'applied_at')
    list_filter = ('project', 'status', 'applied_at')
    search_fields = ('user__fullname', 'user__username', 'user__phone')
    list_per_page = 500 

    # --- ACTIONS (МАССОВЫЕ ДЕЙСТВИЯ) ---
    actions = ['approve_and_invite', 'make_attended_with_msg', 'make_rejected']

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
                asyncio.run(send_notification(obj.user.tg_id, text))
                count += 1
            else:
                self.message_user(request, f"Ошибка: У проекта '{obj.project.title}' нет ссылки!", messages.ERROR)
        
        self.message_user(request, f"Одобрено и отправлено сообщений: {count}")

    @admin.action(description='🌟 Пришёл на эвент (+10 баллов + Уведомление)')
    def make_attended_with_msg(self, request, queryset):
        for obj in queryset:
            if obj.status != 'attended':
                obj.status = 'attended'
                obj.save() # Начислит баллы в модели
                
                text = (
                    f"🌟 <b>Rahmat!</b>\n\n"
                    f"Siz bugungi loyihada faol qatnashdingiz va <b>10 eko-ball</b> oldingiz!\n"
                    f"Hozirgi balansingiz: <b>{obj.user.balance}</b> ball.\n\n"
                    f"<i>Yana bir oz yig'ing va sovg'alarga almashtiring!</i>"
                )
                asyncio.run(send_notification(obj.user.tg_id, text))
        self.message_user(request, "Баллы начислены, пользователи уведомлены!")

    @admin.action(description='❌ Отменить участие (Удалить баллы)')
    def make_rejected(self, request, queryset):
        for obj in queryset:
            obj.status = 'rejected'
            obj.save()

    # --- ОТОБРАЖЕНИЕ ФОТО ---
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

# --- 3. ОСТАЛЬНЫЕ РЕГИСТРАЦИИ ---

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
    # Добавляем возможность редактировать ссылку прямо в списке
    list_editable = ('is_active',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock')
    list_editable = ('price', 'stock')

admin.site.register(Partner)
admin.site.register(TeamMemberYashilQullar)