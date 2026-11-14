import os
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = env("SECRET_KEY")  # noqa: F405
if SECRET_KEY.startswith("unsafe-") or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("Set a randomly generated SECRET_KEY of at least 50 characters.")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])  # noqa: F405
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set explicit ALLOWED_HOSTS entries; wildcards are not allowed.")

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires PostgreSQL. Set DATABASE_URL to the production database.")
DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
if any(
    urlsplit(origin).scheme != "https"
    or not urlsplit(origin).netloc
    or urlsplit(origin).path not in {"", "/"}
    or urlsplit(origin).query
    or urlsplit(origin).fragment
    for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured("CSRF_TRUSTED_ORIGINS entries must use HTTPS.")
if _render_host:
    _origin = f"https://{_render_host}"
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)

ALLOW_LOCAL_MEDIA = False

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405

# Share throttling counters across Gunicorn workers and service instances.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache_table",
        "TIMEOUT": 300,
    }
}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
