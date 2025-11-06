"""
Base settings for VeriFlow — eKYC/KYA Platform
- Django 4.x / DRF 3.x
- Multi-tenant logique
- Auth API-Key + HMAC
- Celery + Redis
- S3 (optionnel) + antivirus (branché côté storage app)
- drf-spectacular (Swagger & ReDoc)
- Observabilité (OTel hooks + logging structuré)
"""


from pathlib import Path
import os
import sys
import json
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------------------
# ENV
# ------------------------------------------------------------------------------
def env(key: str, default=None, cast=None):
    val = os.getenv(key, default)
    if cast and val is not None:
        try:
            return cast(val)
        except Exception:
            return default
    return val

SECRET_KEY = env("SECRET_KEY", "change-me")
DEBUG = False  # override in dev.py

ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

# ------------------------------------------------------------------------------
# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
]

LOCAL_APPS = [
    "core",
    "tenants",
    "apikeys",
    "limits",
    "billing",
    "usage",
    "audit",
    "observability",
    "storage",
    "webhooks",
    "jobs",
    "docs",
    "backoffice",
    "kyc",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ------------------------------------------------------------------------------
# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Observabilité (correlation id / OTel) — hooks app observability ajoutera si besoin
]

ROOT_URLCONF = "veriflow.urls"
WSGI_APPLICATION = "veriflow.wsgi.application"
ASGI_APPLICATION = "veriflow.asgi.application"

# ------------------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------------------
# Support DATABASE_URL=postgres://user:pass@host:port/dbname
def parse_database_url(url: str):
    if not url:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "veriflow"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PORT", "5432"),
        }
    o = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": o.path.lstrip("/") or "veriflow",
        "USER": o.username or "",
        "PASSWORD": o.password or "",
        "HOST": o.hostname or "127.0.0.1",
        "PORT": str(o.port or "5432"),
    }

DATABASES = {
    "default": parse_database_url(env("DATABASE_URL"))
}

# ------------------------------------------------------------------------------
# AUTH / USERS
# ------------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------------------
# I18N / TZ
# ------------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------------------
# STATIC & MEDIA
# ------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# S3 optionnel via django-storages
S3_BUCKET = env("S3_BUCKET", "")
if S3_BUCKET:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", None)
    AWS_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME = S3_BUCKET
    AWS_S3_REGION_NAME = env("S3_REGION", None)
    AWS_QUERYSTRING_AUTH = False

# ------------------------------------------------------------------------------
# REST FRAMEWORK (DRF)
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apikeys.auth.hmac.ApiKeyHmacAuthentication",  # HMAC + API KEY
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "core.permissions.tenant_scoped.TenantScopedPermission",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "limits.throttling.TenantMinuteThrottle",
        "limits.throttling.TenantDailyThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",  # valeurs par défaut (overriden par plan/tenant dans limits)
    },
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# Spectacular (OpenAPI)
SPECTACULAR_SETTINGS = {
    "TITLE": env("OPENAPI_TITLE", "VeriFlow API"),
    "DESCRIPTION": "API eKYC/KYA (liveness, OCR, validation documentaire, face-match, workflow).",
    "VERSION": env("OPENAPI_VERSION", "1.0.0"),
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "CONTACT": {"name": "VeriFlow Support", "email": "support@example.com"},
    "LICENSE": {"name": "Proprietary"},
    "TOS": "https://example.com/terms",
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_AUTHENTICATION": [],
}

# ------------------------------------------------------------------------------
# CELERY
# ------------------------------------------------------------------------------
CELERY_BROKER_URL = env("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TIME_LIMIT = 60 * 10  # 10 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 5
CELERY_TASK_ROUTES = {
    "webhooks.tasks.deliver_webhook_task": {"queue": "webhooks"},
}
CELERY_BEAT_SCHEDULE = {
    # Exemple: jobs de purge/usage/quotas seront ajoutés plus tard
}

# ------------------------------------------------------------------------------
# UPLOAD POLICIES
# ------------------------------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640

# ------------------------------------------------------------------------------
# SECURITY
# ------------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "same-origin"

# ------------------------------------------------------------------------------
# LOGGING (JSON friendly)
# ------------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "logging.Formatter",
            "format": '{"ts":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s","msg":"%(message)s","module":"%(module)s","line":%(lineno)d}',
        },
        "simple": {"format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if env("LOG_JSON", "1") == "1" else "simple",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "veriflow": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# ------------------------------------------------------------------------------
# OPEN TELEMETRY (opt-in via env)
# ------------------------------------------------------------------------------
OTEL_ENABLED = env("OTEL_ENABLED", "0") == "1"
OTEL_EXPORTER_OTLP_ENDPOINT = env("OTEL_EXPORTER_OTLP_ENDPOINT", "")

# ------------------------------------------------------------------------------
# API VERSIONING
# ------------------------------------------------------------------------------
API_PREFIX = "api"
API_VERSION = "v1"

# ------------------------------------------------------------------------------
# HEALTHCHECK
# ------------------------------------------------------------------------------
def HEALTH_INFO():
    return {
        "name": "VeriFlow",
        "version": SPECTACULAR_SETTINGS["VERSION"],
        "env": "prod" if not DEBUG else "dev",
    }

# ------------------------------------------------------------------------------
# TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Optionnel mais pratique si vous avez un dossier templates/ à la racine
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]