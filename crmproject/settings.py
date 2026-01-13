# Security & Environment
import os
from pathlib import Path
import environ

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Load .env file from project root
environ.Env.read_env(env_file=BASE_DIR / ".env")

# SECRET KEY
SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")

# Debug & Hosts
# Debug
DEBUG = env.bool("DEBUG", default=False)

# Allowed hosts
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "crm.isecuresolutions.in",
        "www.crm.isecuresolutions.in",
        "isecuresolutions.in",
        "www.isecuresolutions.in",
    ],
)

# CSRF trusted origins (MUST include https://)
CSRF_TRUSTED_ORIGINS = [
    "https://crm.isecuresolutions.in",
    "https://www.crm.isecuresolutions.in",
    "https://isecuresolutions.in",
    "https://www.isecuresolutions.in",
]

# Custom User Model
AUTH_USER_MODEL = "crm.User"

# Static & Media
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEBUG = env.bool("DEBUG", default=False)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# Auth redirects
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    'widget_tweaks',
    "crm",
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
]

ROOT_URLCONF = "crmproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "crm" / "templates",
            BASE_DIR / "templates",
        ],
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

WSGI_APPLICATION = "crmproject.wsgi.application"

# Database (PostgreSQL for Render, fallback to SQLite locally)
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True





