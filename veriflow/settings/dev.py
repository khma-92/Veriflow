from .base import *

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Cookies non sécurisés en dev
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# DRF renderers plus larges en dev (browsable API si tu veux)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# Email console pour dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Swagger/ReDoc accessibles sans auth en dev (déjà AllowAny via spectacular)
