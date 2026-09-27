from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppTelegramConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_telegram'
    verbose_name = "Yashil Qo'llar"

    def ready(self):
        import app_telegram.translation  # noqa
        # ⏳ лист ожидания: место освободилось → записываем первого из очереди
        from django.db.models.signals import post_delete, post_save
        from . import waitlist
        from .models import ProjectParticipation, EcoProject
        post_delete.connect(waitlist.on_participation_deleted, sender=ProjectParticipation, dispatch_uid="wait_del")
        post_save.connect(waitlist.on_participation_saved, sender=ProjectParticipation, dispatch_uid="wait_save")
        post_save.connect(waitlist.on_project_saved, sender=EcoProject, dispatch_uid="wait_proj")
        