import os
import sys
from urllib.parse import urlsplit
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "Lazuna"
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
if PUBLIC_BASE_URL and (urlsplit(PUBLIC_BASE_URL).scheme != "https" or not urlsplit(PUBLIC_BASE_URL).hostname or urlsplit(PUBLIC_BASE_URL).path or urlsplit(PUBLIC_BASE_URL).query or urlsplit(PUBLIC_BASE_URL).fragment or urlsplit(PUBLIC_BASE_URL).username):
    raise ImproperlyConfigured("PUBLIC_BASE_URL debe ser un origen HTTPS sin rutas ni credenciales.")

APP_VERSION = (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip()

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY and not DEBUG:
    # Docker's entrypoint stores the generated key in the private data volume
    # so management commands executed later in the same container use it too.
    secret_file = Path(os.environ.get("DJANGO_SECRET_FILE", "/data/.django_secret_key"))
    if secret_file.is_file():
        SECRET_KEY = secret_file.read_text(encoding="utf-8").strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "development-only-change-before-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY es obligatoria cuando DJANGO_DEBUG=0.")
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
if PUBLIC_BASE_URL:
    ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, urlsplit(PUBLIC_BASE_URL).hostname]))
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, PUBLIC_BASE_URL]))

FORCE_HTTPS = os.environ.get("DJANGO_FORCE_HTTPS", "0") == "1"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "organizations.backends.EmailBackend",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "organizations",
    "patients",
    "grooming",
    "inventory",
    "sales",
    "visits",
    "lost_pets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "organizations.auth_limits.AuthAttemptLimitMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
# Railway supplies X-Real-IP at its public edge. Local/direct deployments ignore it.
# Disable this if exposing an origin directly or using a different ingress proxy.
AUTH_TRUST_RAILWAY_PROXY = os.environ.get(
    "DJANGO_AUTH_TRUST_RAILWAY_PROXY", "1" if os.environ.get("RAILWAY_ENVIRONMENT_ID") else "0",
) == "1"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "organizations.context_processors.business_profile",
        "organizations.context_processors.application_version",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
        "OPTIONS": {"timeout": 20},
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if "test" in sys.argv:
    # The test runner does not run collectstatic, so a production manifest is
    # intentionally unavailable there. Runtime production settings stay intact.
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
MEDIA_URL = "media/"
MEDIA_ROOT = os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media")
SERVE_MEDIA = os.environ.get("DJANGO_SERVE_MEDIA", "0") == "1"
EXPO_PUSH_ACCESS_TOKEN = os.environ.get("EXPO_PUSH_ACCESS_TOKEN", "")
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "587"))
EMAIL_TIMEOUT = 10
EMAIL_USE_TLS = os.environ.get("DJANGO_EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "Lazuna <no-reply@localhost>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
if FORCE_HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
