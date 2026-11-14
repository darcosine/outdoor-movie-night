from .base import *  # noqa: F403

DEBUG = True

# runserver serves static files directly during local development.
MIDDLEWARE = [
    item for item in MIDDLEWARE
    if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]
ALLOWED_HOSTS = env.list(  # noqa: F405
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "testserver"],
)
if "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")

ALLOW_LOCAL_MEDIA = True

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

