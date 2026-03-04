import os
import sys
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

if sys.version_info < (3, 9):
    raise ImproperlyConfigured("TimePoll requires Python 3.9 or newer.")

BASE_DIR = Path(__file__).resolve().parent.parent

def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ImproperlyConfigured(f"{name} environment variable is required.")
    cleaned = value.strip()
    if not cleaned:
        raise ImproperlyConfigured(f"{name} environment variable cannot be empty.")
    return cleaned


def parse_env_bool(name: str) -> bool:
    raw = require_env(name).lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(
        f"{name} must be a boolean-like value: 1/0, true/false, yes/no, on/off."
    )


def parse_env_list(name: str) -> list[str]:
    raw = require_env(name)
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        raise ImproperlyConfigured(f"{name} must contain at least one value.")
    return values


SECRET_KEY = require_env("TIMEPOLL_SECRET_KEY")
DEBUG = parse_env_bool("TIMEPOLL_DEBUG")

ALLOWED_HOSTS = parse_env_list("TIMEPOLL_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "polls",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "timepoll.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "timepoll.wsgi.application"
ASGI_APPLICATION = "timepoll.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

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

LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    ("fi", "Finnish"),
    ("no", "Norwegian"),
    ("sv", "Swedish"),
    ("et", "Estonian"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
