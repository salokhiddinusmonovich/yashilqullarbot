"""Кнопки напоминаний: «🌿 QR-kod» и «❌ Kelolmayman» (tgbot/services/reminders.py)."""
from aiogram import types, Dispatcher
from asgiref.sync import sync_to_async

from tgbot.i18n import t


@sync_to_async
def _cancel(tg_id: int, project_id: int):
    """Освободить место: запись «записан» удаляем, «пришёл» не трогаем. Отмечаем для координатора."""
    from app_telegram.models import ProjectParticipation
    from tgbot.services.lang import _sclient
    p = ProjectParticipation.objects.filter(user__tg_id=tg_id, project_id=project_id).select_related('project').first()
    if not p:
        return "none", None
    if p.status == 'attended':
        return "attended", p.project.title
    title = p.project.title
    p.delete()
    try:
        _sclient().sadd(f"cancel:{project_id}", tg_id)
        _sclient().expire(f"cancel:{project_id}", 60 * 86400)
    except Exception:
        pass
    return "ok", title


async def rem_callback(call: types.CallbackQuery):
    parts = call.data.split(":")
    if parts[1] == "qr":
        from .qr_handler import send_qr
        await call.answer()
        await send_qr(call.message, call.from_user.id)
        return
    if parts[1] == "no":
        res, title = await _cancel(call.from_user.id, int(parts[2]))
        await call.answer()
        if res == "ok":
            try:
                await call.message.edit_reply_markup(None)
            except Exception:
                pass
            await call.message.answer(t("rem_cancelled", title=title))
        elif res == "attended":
            await call.message.answer(t("rem_cant_cancel"))
        else:
            await call.message.answer(t("rem_not_found"))


def register_reminders(dp: Dispatcher):
    dp.register_callback_query_handler(rem_callback, lambda c: c.data.startswith("rem:"), state="*")
