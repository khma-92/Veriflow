from .base import *

DEBUG = False

# À configurer explicitement en prod
ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]

# Cookies sécurisés
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# HSTS (ajuster selon politique)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Headers sécurité supplémentaires
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True

# Logging JSON forcé
LOGGING["handlers"]["console"]["formatter"] = "json"
