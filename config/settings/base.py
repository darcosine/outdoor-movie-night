"""Shared settings. Environment comes from django-environ; the database URL from dj-database-url."""

from datetime import date
from pathlib import Path

import dj_database_url
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    environ.Env.read_env(_env_file)

SECRET_KEY = env("SECRET_KEY", default="unsafe-dev-key-change-me-please-32chars")
DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "registrations",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "registrations.context_processors.event",
            ],
        },
    }
]

_sqlite_default = "sqlite:///" + (BASE_DIR / "db.sqlite3").as_posix()
DATABASES = {
    "default": dj_database_url.config(
        default=_sqlite_default,
        conn_max_age=env.int("DB_CONN_MAX_AGE", default=0),
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "movie-night",
    }
}

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

# Money. Registration.amount_due is rupees. Payment.amount is paise (PhonePe).
PAY_RUPEES = 500
PAY_PAISE = 50000
RESERVE_RUPEES = 600
DOOR_SURCHARGE_RUPEES = 100

EVENT = {
    "title": "Outdoor Movie Night",
    "when": "Friday, 13 November 2026",
    "date": "2026-11-13",
    "where": "Campus lawn",
    "gates": "6:00 pm",
    "screening": "Dusk",
    "contact_email": "movienight@example.com",
}
EVENT_DATE = date.fromisoformat(EVENT["date"])

PHONEPE_MERCHANT_ID = env("PHONEPE_MERCHANT_ID", default="")
PHONEPE_SALT_KEY = env("PHONEPE_SALT_KEY", default="")
PHONEPE_SALT_INDEX = env("PHONEPE_SALT_INDEX", default="1")
PHONEPE_BASE_URL = env(
    "PHONEPE_BASE_URL",
    default="https://api-preprod.phonepe.com/apis/pg-sandbox",
)
PHONEPE_REDIRECT_URL = env(
    "PHONEPE_REDIRECT_URL",
    default="http://127.0.0.1:8000/payments/return/",
)
PHONEPE_CALLBACK_URL = env(
    "PHONEPE_CALLBACK_URL",
    default="http://127.0.0.1:8000/payments/callback/",
)
PHONEPE_MOCK = env.bool("PHONEPE_MOCK", default=True)

CLOUDINARY_URL = env("CLOUDINARY_URL", default="")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_PUBLIC_URL = env("AWS_S3_PUBLIC_URL", default="")
AWS_S3_REGION = env("AWS_S3_REGION", default="auto")

ID_CARD_MAX_BYTES = 5 * 1024 * 1024
ID_CARD_MIN_WIDTH = 480
ID_CARD_MIN_HEIGHT = 300
ID_CARD_MAX_EDGE = 8000

ALLOW_LOCAL_MEDIA = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "registrations": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

