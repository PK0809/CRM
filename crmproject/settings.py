# =====================================
# Security & Environment
# =====================================
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="change-me-in-production")
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[
    "localhost",
    "127.0.0.1",
    "192.168.31.194",
    "crm.isecuresolutions.in",
    "www.crm.isecuresolutions.in",
    ".cfargotunnel.com",
    ".onrender.com",
])

# =====================================
# Proxy / SSL header
# =====================================
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# =====================================
# Applications
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
# URL / WSGI
# =====================================
ROOT_URLCONF = "crmproject.urls"
WSGI_APPLICATION = "crmproject.wsgi.application"

# =====================================
# Templates
# =====================================
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

# =====================================
# Database (SQLite for local, Postgres for production)
# =====================================
if env.bool("USE_POSTGRES", default=False):
    # Production / live DB
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env("DB_NAME"),
            'USER': env("DB_USER"),
            'PASSWORD': env("DB_PASS"),
            'HOST': env("DB_HOST"),
            'PORT': env("DB_PORT", default="5432"),
        }
    }
else:
    # Local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =====================================
# Auth & Users
# =====================================
AUTH_USER_MODEL = "crm.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =====================================
# Static & Media
# =====================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # For collectstatic in production

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Local static directories (only if DEBUG)
STATICFILES_DIRS = [BASE_DIR / "crm" / "static"]
if DEBUG:
    STATICFILES_DIRS.append(BASE_DIR / "static_dev")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# PDF logo fix
SITE_URL = env("SITE_URL", default="https://crm.isecuresolutions.in")

# =====================================
# Authentication Redirects
# =====================================
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

# =====================================
# Internationalization
# =====================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
