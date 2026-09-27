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
