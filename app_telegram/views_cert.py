"""GET /c/<id>-<подпись>.pdf|jpg — сертификат участника (ссылка из бота и Mini App)."""
from django.http import Http404, HttpResponse
from django.views.decorators.cache import cache_control

from . import certificates as C


@cache_control(private=True, max_age=3600)
def certificate_file(request, pid: int, sig: str, ext: str):
    if ext not in ("pdf", "jpg") or not C.verify(pid, sig):
        raise Http404
    pp = C.attended(pid)
    if not pp:
        raise Http404
    img = C.render_for(pp)
    if ext == "pdf":
        resp = HttpResponse(C.to_pdf(img), content_type="application/pdf")
    else:
        resp = HttpResponse(C.to_jpg(img, max_w=1200 if request.GET.get("small") else None), content_type="image/jpeg")
    resp["Content-Disposition"] = f'inline; filename="{C.filename(pp, ext)}"'
    return resp


@cache_control(private=True, max_age=600)
def cv_file(request, uid: int, sig: str):
    """GET /c/cv/<id>-<подпись>.pdf — 📄 Volontyor CV."""
    from . import cv
    from .models import TGUser
    if not cv.verify(uid, sig):
        raise Http404
    user = TGUser.objects.filter(pk=uid).first()
    if not user:
        raise Http404
    from tgbot.services.lang import lang_of_sync
    lang = request.GET.get("lang") or (lang_of_sync(user.tg_id) if user.tg_id else "uz")
    resp = HttpResponse(cv.build(user, lang if lang in ("uz", "ru", "en") else "uz"), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{cv.filename(user)}"'
    return resp


def certificate_verify(request, pid: int, sig: str):
    """GET /c/v/<id>-<подпись> — публичная проверка подлинности (сюда ведёт QR на сертификате)."""
    from django.shortcuts import render
    from django.utils import timezone
    from tgbot.i18n import region_label
    pp = C.attended(pid) if C.verify_short(pid, sig) else None
    ctx = {"ok": bool(pp)}
    if pp:
        ctx.update({
            "name": C.display_name(pp.user.fullname), "event": pp.project.title,
            "date": timezone.localtime(pp.project.date).strftime("%d.%m.%Y") if pp.project.date else "",
            "region": region_label(pp.project.region, "uz") if pp.project.region else "",
            "number": C.number_of(pp), "img": C.url(pp.id, "jpg") + "?small=1", "pdf": C.url(pp.id, "pdf"),
        })
    return render(request, "cert_verify.html", ctx, status=200 if pp else 404)
