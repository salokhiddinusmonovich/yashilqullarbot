from django.contrib import admin

from app_telegram.models import TGUser, TeamMemberYashilQullar,ProjectParticipation,EcoProject


class TGUserAdmin(admin.ModelAdmin):
    list_display = ['tg_id', 'created']
    list_filter = ['created', ]
    search_fields = ['tg_id', ]
    save_on_top = True


admin.site.register(TGUser, TGUserAdmin)

admin.site.register(TeamMemberYashilQullar)
admin.site.register(ProjectParticipation)
admin.site.register(EcoProject)
