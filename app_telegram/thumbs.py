"""
Уменьшенные копии картинок для Mini App: фото мероприятия в оригинале
бывает на 3–8 МБ, а на экране телефона нужно ~800px по ширине.
Копия создаётся один раз при первом запросе и дальше отдаётся как файл.
"""
import logging
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)


def thumb_url(field, width: int = 800) -> str | None:
    if not field:
        return None
    try:
        src = Path(field.path)
    except Exception:
        return None
    rel = Path(field.name)
    dst_rel = Path("thumbs") / f"{width}" / rel.with_suffix(".jpg")
    dst = Path(settings.MEDIA_ROOT) / dst_rel
    try:
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            dst.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((width, width * 2))
                im.save(dst, "JPEG", quality=78, optimize=True, progressive=True)
    except Exception as e:
        logger.warning("thumbnail failed for %s: %s", src, e)
        return field.url
    return settings.MEDIA_URL.rstrip("/") + "/" + dst_rel.as_posix()
