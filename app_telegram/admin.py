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

BOT_TOKEN = "8597081931:AAHrLlthINCN8nIZp_zh3WEbzfc-5GhoHmw"

async def send_notification(user_id, text):
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
    finally:
        await bot.close()

class ParticipationResource(resources.ModelResource):
    username = Field(attribute='user__username', column_name='Telegram Username')
    fullname = Field(attribute='user__fullname', column_name='F.I.SH (Имя)')
    phone = Field(attribute='user__phone', column_name='Telefon')
    experience = Field(attribute='user__experience', column_name='Tajribasi (Опыт)')
    
    # НОВОЕ: Ссылка на фото
    photo_url = Field(column_name='Rasm (Ссылка на фото)')

    project_name = Field(attribute='project__title', column_name='Loyiha nomi')

    class Meta:
        model = ProjectParticipation
        # Добавляем photo_url в список полей
        fields = ('username', 'fullname', 'phone', 'experience', 'photo_url', 'project_name', 'status')
        export_order = fields

    # Логика для создания полной ссылки
    def dehydrate_photo_url(self, obj):
        if obj.user and obj.user.photo:
            # Замени 'http://твой-ip-или-домен' на реальный URL твоего сервера
            server_url = "http://173.249.19.32:8000" 
            return f"{server_url}{obj.user.photo.url}"
        return "Нет фото"
        

# --- 2. ГЛАВНАЯ АДМИНКА УЧАСТНИКОВ ---
@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = ParticipationResource
    
    # Теперь ты видишь ИМЯ, ПРОЕКТ и СТАТУС рядом.
    list_display = ('display_face', 'get_fullname', 'get_project_title', 'status_colored', 'applied_at')
    
    # ЭТО ГЛАВНОЕ: Фильтр по проекту. Справа в админке будет список ивентов.
    list_filter = (('project', admin.RelatedOnlyFieldListFilter), 'status', 'applied_at')
    
    search_fields = ('user__fullname', 'user__username', 'user__phone', 'project__title')
    list_per_page = 50 
    
    # Позволяет менять статус прямо в списке, не заходя внутрь юзера
    list_editable = ('status',)

    actions = ['approve_and_invite', 'make_attended_with_msg', 'make_rejected']

    # Красивое отображение статуса с цветами
    def status_colored(self, obj):
        colors = {
            'approved': '#28a745', # Зеленый
            'pending': '#ffc107',  # Желтый
            'rejected': '#dc3545', # Красный
            'attended': '#17a2b8', # Голубой
        }
        return format_html(
            '<b style="color: {}; text-transform: uppercase;">{}</b>',
            colors.get(obj.status, 'black'),
            obj.status
        )
    status_colored.short_description = 'СТАТУС'

    def get_project_title(self, obj):
        return obj.project.title
    get_project_title.short_description = 'ПРОЕКТ (Loyiha)'

    # --- Твои ACTIONS остаются такими же, но теперь они работают точнее ---
    @admin.action(description='✅ Одобрить и отправить ССЫЛКУ')
    def approve_and_invite(self, request, queryset):
        # Если ты отфильтровал по проекту "Eco-Day", 
        # то queryset будет содержать только людей из этого проекта.
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
        self.message_user(request, f"Yuborildi: {count}")


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


# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ('name', 'price', 'stock')
#     list_editable = ('price', 'stock')

admin.site.register(Partner)
