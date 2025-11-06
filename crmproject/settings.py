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
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "127.0.0.1",
        "localhost",
        "crm.isecuresolutions.in",
        "www.crm.isecuresolutions.in",
        "isecuresolutions.in",
        "www.isecuresolutions.in",
    ],
)

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

import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.environ.get('USE_SQLITE', '1') == '1':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': os.environ.get('PGHOST', '127.0.0.1'),
            'PORT': os.environ.get('PGPORT', '5432'),
            'NAME': os.environ.get('PGDATABASE', ''),
            'USER': os.environ.get('PGUSER', ''),
            'PASSWORD': os.environ.get('PGPASSWORD', ''),
            'CONN_MAX_AGE': 60,
        }
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

DEBUG = True
