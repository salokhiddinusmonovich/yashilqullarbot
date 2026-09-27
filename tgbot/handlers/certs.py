"""🎓 /sertifikat — все мои сертификаты кнопками; нажал — бот присылает PDF."""
from html import escape
from io import BytesIO

from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from asgiref.sync import sync_to_async
from django.utils import timezone

from tgbot.i18n import t


@sync_to_async
def _my(tg_id: int):
    from app_telegram.models import ProjectParticipation
    return list(ProjectParticipation.objects.filter(user__tg_id=tg_id, status='attended')
                .select_related('project').order_by('-project__date')[:40])


async def certs_handler(message: types.Message):
    items = await _my(message.from_user.id)
    if not items:
        await message.answer(t("cert_none"))
        return
    kb = InlineKeyboardMarkup(row_width=1)
    for pp in items:
        d = timezone.localtime(pp.project.date).strftime('%d.%m.%Y')
        kb.add(InlineKeyboardButton(f"🎓 {d} · {pp.project.title[:40]}", callback_data=f"cert:{pp.id}"))
    await message.answer(t("cert_list", n=len(items)), reply_markup=kb)


@sync_to_async
def _pdf_for(pid: int, tg_id: int):
    from app_telegram import certificates as C
    pp = C.attended(pid)
    if not pp or pp.user.tg_id != tg_id:    # только свой сертификат
        return None
    return C.to_pdf(C.render_for(pp)), C.filename(pp), C.number_of(pp), pp.project.title


async def cert_callback(call: types.CallbackQuery):
    await call.answer(t("adm_preparing"))
    res = await _pdf_for(int(call.data.split(":")[1]), call.from_user.id)
    if not res:
        await call.message.answer(t("cert_none"))
        return
    data, fname, number, title = res
    await call.message.answer_document(InputFile(BytesIO(data), filename=fname),
                                       caption=t("cert_caption", title=escape(title), number=number))


@sync_to_async
def _cv(tg_id: int, lang: str):
    from app_telegram import cv
    from app_telegram.models import TGUser
    u = TGUser.objects.filter(tg_id=tg_id).first()
    return (cv.build(u, lang), cv.filename(u)) if u else (None, None)


async def cv_handler(message: types.Message):
    from tgbot.i18n import current_lang
    await message.answer(t("adm_preparing"))
    data, fname = await _cv(message.from_user.id, current_lang.get() or "uz")
    if not data:
        await message.answer(t("cert_none"))
        return
    await message.answer_document(InputFile(BytesIO(data), filename=fname), caption=t("cv_caption"))


def register_certs(dp: Dispatcher):
    dp.register_message_handler(cv_handler, commands=["cv", "rezyume", "резюме"], state="*")
    dp.register_message_handler(certs_handler, commands=["sertifikat", "certificate", "certificates", "cert"], state="*")
    dp.register_callback_query_handler(cert_callback, lambda c: c.data.startswith("cert:"), state="*")
