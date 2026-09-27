"""
⏳ Лист ожидания на заполненные мероприятия.

Мест нет → человек встаёт в очередь (Redis db 6, как язык: wait:<id мероприятия> —
упорядоченное множество id людей по времени). Освободилось место (кто-то нажал
«❌ Kelolmayman», админ удалил/отклонил запись, увеличили число мест) —
первого в очереди записываем автоматически (status «записан») и бот ему пишет.
Схему БД не трогаем. Сигналы подключаются в apps.py.
"""
import logging
import time
from html import escape

log = logging.getLogger(__name__)


def _r():
    from tgbot.services.lang import _sclient
    return _sclient()


def _key(pid: int) -> str:
    return f"wait:{pid}"


def join(user, project) -> int | None:
    """Встать в очередь. Возвращает место (1, 2, …)."""
    try:
        r = _r()
        r.zadd(_key(project.id), {str(user.id): time.time()}, nx=True)
        r.expire(_key(project.id), 90 * 86400)
        rank = r.zrank(_key(project.id), str(user.id))
        return None if rank is None else rank + 1
    except Exception as e:
        log.warning("waitlist join: %s", e)
        return None


def leave(user_id: int, pid: int):
    try:
        _r().zrem(_key(pid), str(user_id))
    except Exception:
        pass


def position(user_id: int, pid: int) -> int | None:
    try:
        rank = _r().zrank(_key(pid), str(user_id))
        return None if rank is None else rank + 1
    except Exception:
        return None


def count(pid: int) -> int:
    try:
        return int(_r().zcard(_key(pid)))
    except Exception:
        return 0


def promote(project) -> list:
    """Пока есть свободные места — записываем первых из очереди. Возвращает список записанных."""
    from .models import TGUser, ProjectParticipation
    from .services import region_group
    if not project or not project.is_active:
        return []
    promoted = []
    try:
        r = _r()
        while True:
            taken = project.participants.exclude(status='rejected').count()
            if taken >= project.max_participants:
                break
            first = r.zrange(_key(project.id), 0, 0)
            if not first:
                break
            r.zrem(_key(project.id), first[0])
            user = TGUser.objects.filter(id=int(first[0])).first()
            if not user or project.region not in region_group(user.region):
                continue
            _, created = ProjectParticipation.objects.get_or_create(user=user, project=project, defaults={'status': 'approved'})
            if created:
                promoted.append(user)
    except Exception as e:
        log.warning("waitlist promote: %s", e)
    if promoted:
        _notify(project, promoted)
    return promoted


def _notify(project, users):
    try:
        from django.utils import timezone
        from tgbot.i18n import t as bot_t
        from tgbot.services.lang import langs_of_sync
        from .telegram import send_in_background
        langs = langs_of_sync([u.tg_id for u in users if u.tg_id])
        when = timezone.localtime(project.date).strftime('%d.%m %H:%M') if project.date else ""
        msgs = []
        for u in users:
            if not u.tg_id:
                continue
            lang = langs.get(u.tg_id)
            text = bot_t("wait_promoted", lang, title=escape(project.title), when=when)
            if project.chat_link:
                text += bot_t("event_accepted_chat", lang, link=project.chat_link)
            msgs.append((u.tg_id, text))
        if msgs:
            send_in_background(msgs)
    except Exception as e:
        log.warning("waitlist notify: %s", e)


# ─────────── сигналы: место освободилось ───────────

def on_participation_deleted(sender, instance, **kwargs):
    # удаляют само мероприятие (каскадом уходят и записи) — никого не записываем
    from .models import EcoProject
    origin = kwargs.get("origin")
    if isinstance(origin, EcoProject) or getattr(origin, "model", None) is EcoProject:
        return
    try:
        promote(instance.project)
    except Exception as e:
        log.warning("waitlist on delete: %s", e)


def on_participation_saved(sender, instance, created, **kwargs):
    if instance.status == 'rejected':
        try:
            promote(instance.project)
        except Exception as e:
            log.warning("waitlist on reject: %s", e)


def on_project_saved(sender, instance, created, **kwargs):
    if not created:
        promote(instance)      # могли увеличить число мест
