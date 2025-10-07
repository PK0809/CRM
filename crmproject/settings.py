import os
from pathlib import Path
import environ
import dj_database_url

# =====================================
# Base directory
# =====================================
BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================
# Initialize django-environ
# =====================================
env = environ.Env(
    DEBUG=(bool, True),
)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)
else:
    print("⚠️ .env file not found at", env_file)

# =====================================
# Security & Environment
# =====================================
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# =====================================
# SSL / Proxy settings for Render
# =====================================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
CSRF_TRUSTED_ORIGINS = [
    "https://crm.isecuresolutions.in",
    "https://www.crm.isecuresolutions.in",
    "https://*.onrender.com",
    "https://*.cfargotunnel.com",
]

# =====================================
# Installed apps
# =====================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "crm",
]

# =====================================
# Middleware
# =====================================
MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =====================================
# URL & WSGI
# =====================================
ROOT_URLCONF = "crmproject.urls"
WSGI_APPLICATION = "crmproject.wsgi.application"

# =====================================
# Templates
# =====================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "crm" / "templates", BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "crm.context_processors.global_logo_path",
            ],
        },
    },
]

# =====================================
# Database (Render PostgreSQL)
# =====================================
DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=False,  # ✅ prevent duplicate SSL enforcement
    )
}

# ✅ Add SSL mode for Django safely
DATABASES["default"]["OPTIONS"] = {
    "sslmode": "require"
}

# =====================================
# Authentication
# =====================================
AUTH_USER_MODEL = "crm.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

# =====================================
# Static & Media files
# =====================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STATICFILES_DIRS = [BASE_DIR / "crm" / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

SITE_URL = env("SITE_URL")

# =====================================
# Internationalization
# =====================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
