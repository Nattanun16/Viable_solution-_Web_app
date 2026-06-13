"""
Django settings for viable_graph project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# แก้บัค #10: SECRET_KEY ต้องอ่านจาก environment variable ไม่ hardcode
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-g0$)7oy-3o%l44(!lp7fy6fb+9&0b=h1mukdud2(m(sun6%a0(")

# แก้บัค #11: DEBUG และ ALLOWED_HOSTS ควรอ่านจาก env
# ตอน dev ปล่อย DEBUG=True ได้ แต่ production ต้องตั้ง DJANGO_DEBUG=False
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

# Production: ตั้ง ALLOWED_HOSTS ใน env เป็น "yourdomain.com,www.yourdomain.com"
_allowed = os.getenv("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(",") if h.strip()] if _allowed else ["*"] if DEBUG else []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "viable_graph_app",
    "django_recaptcha",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "viable_graph_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "viable_graph_project.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "dbs"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# reCAPTCHA — อ่านจาก environment variables โดยปกติ
RECAPTCHA_SITE_KEY = os.getenv("RECAPTCHA_SITE_KEY", "")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

# For local development/testing only: when DEBUG=True and no keys are provided,
# fall back to Google's public test keys which always pass. These test keys
# must NOT be used in production. The system check from django-recaptcha is
# silenced because test keys intentionally trigger a warning.
if DEBUG and (not RECAPTCHA_SITE_KEY or not RECAPTCHA_SECRET_KEY):
    RECAPTCHA_SITE_KEY = RECAPTCHA_SITE_KEY or "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
    RECAPTCHA_SECRET_KEY = RECAPTCHA_SECRET_KEY or "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

RECAPTCHA_PUBLIC_KEY = RECAPTCHA_SITE_KEY
RECAPTCHA_PRIVATE_KEY = RECAPTCHA_SECRET_KEY
SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# แก้บัค #10: Google Vision API Key อ่านจาก env ไม่ hardcode ใน code
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")