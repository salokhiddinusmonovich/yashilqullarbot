from dj_ac.settings import *  # noqa
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": __import__("os").environ.get("TDB", ":memory:")}}
class _NoMig(dict):
    def __contains__(self, k): return True
    def __getitem__(self, k): return None
MIGRATION_MODULES = _NoMig()
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
