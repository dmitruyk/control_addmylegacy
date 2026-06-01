"""
Django settings for Control AddMyLegacy — TV dashboard at control.addmylegacy.com.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "control.addmylegacy.com"],
)


def _build_csrf_trusted_origins():
    configured = env.list("CSRF_TRUSTED_ORIGINS", default=[])
    if configured:
        return configured
    origins = []
    site_url = env("SITE_URL", default="").strip().rstrip("/")
    if site_url.startswith(("http://", "https://")):
        origins.append(site_url)
    for host in ALLOWED_HOSTS:
        if host in ("localhost", "127.0.0.1"):
            for scheme in ("http", "https"):
                origins.append(f"{scheme}://{host}")
                origins.append(f"{scheme}://{host}:8000")
        else:
            origins.append(f"https://{host}")
            origins.append(f"http://{host}")
    return list(dict.fromkeys(origins))


CSRF_TRUSTED_ORIGINS = _build_csrf_trusted_origins()

DATABASE_URL = env("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.MaintenanceModeMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if DATABASE_URL.startswith("sqlite"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="control_addmylegacy"),
            "USER": env("DB_USER", default="postgres"),
            "PASSWORD": env("DB_PASSWORD", default=env("POSTGRES_PASSWORD", default="postgres")),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }
    if DATABASE_URL.startswith(("postgres://", "postgresql://")):
        DATABASES["default"] = env.db("DATABASE_URL")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="America/Los_Angeles")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SITE_NAME = env("SITE_NAME", default="AddMyLegacy Control")
SITE_URL = env("SITE_URL", default="https://control.addmylegacy.com")
MAIN_SITE_URL = env("MAIN_SITE_URL", default="https://addmylegacy.com")
GOOGLE_ANALYTICS_ID = env("GOOGLE_ANALYTICS_ID", default="").strip()

# Bump on deploy to bust TV browser cache for static assets.
STATIC_BUILD_ID = env("STATIC_BUILD_ID", default="1")

# Auto-refresh interval for the TV dashboard (seconds); 0 disables refresh.
TV_REFRESH_SECONDS = env.int("TV_REFRESH_SECONDS", default=60)

# How often the TV page polls /health/ during deploy recovery (seconds).
TV_HEALTH_POLL_SECONDS = env.int("TV_HEALTH_POLL_SECONDS", default=3)

# When True, / redirects to /updating/ (enable before container restart during deploy).
TV_MAINTENANCE_MODE = env.bool("TV_MAINTENANCE_MODE", default=False)

# Bay Area weather (Open-Meteo, no API key).
TV_WEATHER_TIMEZONE = env("TV_WEATHER_TIMEZONE", default="America/Los_Angeles")
TV_WEATHER_CACHE_SECONDS = env.int("TV_WEATHER_CACHE_SECONDS", default=600)
TV_WEATHER_HOURLY_COUNT = env.int("TV_WEATHER_HOURLY_COUNT", default=6)
TV_WEATHER_LOCATIONS = [
    ("Palo Alto", 37.4419, -122.1430),
    ("San Francisco", 37.7749, -122.4194),
]

# Bay Area earthquakes (USGS, no API key).
TV_EARTHQUAKE_CACHE_SECONDS = env.int("TV_EARTHQUAKE_CACHE_SECONDS", default=600)
TV_EARTHQUAKE_LOOKBACK_DAYS = env.int("TV_EARTHQUAKE_LOOKBACK_DAYS", default=30)
TV_EARTHQUAKE_RECENT_DAYS = env.int("TV_EARTHQUAKE_RECENT_DAYS", default=3)
TV_EARTHQUAKE_MIN_MAGNITUDE = env.float("TV_EARTHQUAKE_MIN_MAGNITUDE", default=2.5)
TV_EARTHQUAKE_LIMIT = env.int("TV_EARTHQUAKE_LIMIT", default=3)
TV_EARTHQUAKE_BBOX = {
    "min_lat": 36.5,
    "max_lat": 38.8,
    "min_lon": -123.5,
    "max_lon": -121.0,
}

# Binance US read-only account widget (API key + secret in .env).
BINANCE_US_API_KEY = env("BINANCE_US_API_KEY", default="")
BINANCE_US_API_SECRET = env("BINANCE_US_API_SECRET", default="")
BINANCE_US_API_BASE = env("BINANCE_US_API_BASE", default="https://api.binance.us")
BINANCE_US_CACHE_SECONDS = env.int("BINANCE_US_CACHE_SECONDS", default=300)
BINANCE_US_HISTORY_DAYS = env.int("BINANCE_US_HISTORY_DAYS", default=90)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "control-addmylegacy",
    }
}

TRUST_PROXY_HEADERS = env.bool("TRUST_PROXY_HEADERS", default=False)
if TRUST_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

USE_HTTPS = env.bool("USE_HTTPS", default=False)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
if USE_HTTPS or not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
