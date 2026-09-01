"""
Кэш Telegram file_id для повторно отправляемых фото.

Без него постер в /about, лого партнёров, фото эко-проектов и даже
персональный QR каждого юзера заново читались с диска и заново
аплоадились в Telegram НА КАЖДЫЙ вызов хендлера — для фото на пару
мегабайт это лишние секунды на ровном месте, хотя после первой же
отправки Telegram уже хранит этот файл у себя и может отдать его по
file_id почти мгновенно, без всякой повторной загрузки.

Кэш переживает перезапуск бота — file_id сохраняются в JSON рядом,
не в БД, чтобы не завязываться на состояние Django-миграций.
"""
import json
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_CACHE_FILE = Path(__file__).resolve().parents[2] / "media" / ".tg_file_id_cache.json"


def _load() -> dict:
    try:
        return json.loads(_CACHE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save(cache: dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(cache))
    except OSError:
        logger.warning("Could not persist Telegram file_id cache to %s", _CACHE_FILE)


_cache = _load()


def file_cache_key(local_path) -> str:
    """
    Ключ на основе пути + mtime файла — если админ заменит фото в Django
    admin, mtime изменится, ключ станет другим, и кэш сам "промахнётся"
    один раз и переотправит уже новый файл. Никакой ручной инвалидации
    не нужно.
    """
    path = Path(local_path)
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        mtime = 0
    return f"file:{path}:{mtime}"


async def send_cached_photo(message, cache_key: str, photo_source: Callable, **kwargs):
    """
    Отправляет фото через `message.answer_photo`, переиспользуя закэшированный
    file_id, если он есть — иначе один раз загружает файл и кэширует
    результат для всех следующих вызовов (в любом чате, не только текущем).

    photo_source — callable без аргументов, вызывается ТОЛЬКО при промахе
    кэша (открывает файл / генерирует картинку) — это важно, чтобы при
    попадании в кэш не тратить время на чтение с диска или генерацию.
    """
    cached_id = _cache.get(cache_key)
    if cached_id:
        try:
            return await message.answer_photo(photo=cached_id, **kwargs)
        except Exception:
            # file_id мог протухнуть (например, после смены токена бота) —
            # просто переотправляем файл заново и перезаписываем кэш ниже.
            logger.info("Cached file_id for %s stale, re-uploading", cache_key)

    photo = photo_source()
    sent = await message.answer_photo(photo=photo, **kwargs)

    try:
        _cache[cache_key] = sent.photo[-1].file_id
        _save(_cache)
    except (IndexError, AttributeError):
        pass

    return sent
