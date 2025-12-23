"""
Django settings for AlertaDengue project.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import ibis
import sentry_sdk
from django.contrib.messages import constants as messages
from django.core.files.storage import FileSystemStorage
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration
from sqlalchemy import create_engine

# Env bootstrap
load_dotenv()
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

# Helpers
def read_admins(value: str) -> Tuple[Tuple[str, str], ...]:
    """Parse ADMINS env var into Django's expected tuple.

    Parameters
    ----------
    value : str
        Comma-separated list of "name:email" items.

    Returns
    -------
    tuple of tuple of str
        e.g., (("Admin One", "one@example.org"), ...).
    """
    if not value:
        return tuple()
    pairs: list[tuple[str, str]] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            name, email = item.split(":", 1)
            pairs.append((name.strip(), email.strip()))
    return tuple(pairs)


def get_ibis_conn(database: Optional[str] = None):
    """Create an Ibis Postgres connection.

    Parameters
    ----------
    database : str, optional
        Database name. Defaults to PSQL_DB.

    Returns
    -------
    ibis.backends.postgres.Backend
        Ibis connection instance.
    """
    db = database or os.getenv("PSQL_DB")
    try:
        return ibis.postgres.connect(
            user=os.getenv("PSQL_USER"),
            password=os.getenv("PSQL_PASSWORD"),
            host=os.getenv("PSQL_HOST"),
            port=os.getenv("PSQL_PORT"),
            database=db,
        )
    except ConnectionError as exc:  # pragma: no cover
        print("Database error for Ibis connection")
        raise exc


def get_sqla_conn(database: Optional[str] = None):
    """Create a SQLAlchemy Postgres engine.

    Parameters
    ----------
    database : str, optional
        Database name. Defaults to PSQL_DB.

    Returns
    -------
    sqlalchemy.engine.Engine
        Engine bound to the given database.
    """
    db = database or os.getenv("PSQL_DB")
    uri = (
        f"postgresql://{os.getenv('PSQL_USER')}:{os.getenv('PSQL_PASSWORD')}"
        f"@{os.getenv('PSQL_HOST')}:{os.getenv('PSQL_PORT')}/{db}"
    )
    try:
        return create_engine(uri)
    except ConnectionError as exc:  # pragma: no cover
        print("Database error for SQLAlchemy connection")
        raise exc


# Paths
ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
APPS_DIR = ROOT_DIR / "AlertaDengue"


# Core flags
DEBUG = os.getenv("DEBUG", "").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = (
    os.getenv("ALLOWED_HOSTS").split(",") if os.getenv("ALLOWED_HOSTS") else []
)
ADMINS = read_admins(os.getenv("ADMINS", ""))

MAINTENANCE_MODE = os.getenv("MAINTENANCE", "False").lower() == "true"
MAINTENANCE_MODE_TEMPLATE = str(APPS_DIR / "dados/templates/503.html")

TIME_ZONE = "America/Sao_Paulo"
LANGUAGE_CODE = "pt-br"
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [str(APPS_DIR / "locale")]
LANGUAGES = (("pt-br", "Português"), ("en-us", "english"), ("es", "Spanish"))


# Apps
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "leaflet",
    "bootstrap4",
    "chunked_upload",
    "manager.router",
    "maintenance_mode",
    "django_celery_results",
    "django_celery_beat",
]

LOCAL_APPS = [
    "dados",
    "gis",
    "forecast",
    "dbf.apps.DbfConfig",
    "api",
    "upload",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

if DEBUG:
    INSTALLED_APPS += ("django_extensions",)


# Middleware
_BASE_MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "maintenance_mode.middleware.MaintenanceModeMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_cprofile_middleware.middleware.ProfilerMiddleware",
]

if DEBUG:
    MIDDLEWARE = tuple(_BASE_MIDDLEWARE)
    DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False
else:
    MIDDLEWARE = tuple(
        ["django.middleware.cache.UpdateCacheMiddleware"]
        + _BASE_MIDDLEWARE
        + ["django.middleware.cache.FetchFromCacheMiddleware"]
    )

# Messages
MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}


# Uploads (chunked)
CHUNKED_UPLOAD_PATH = "uploaded/chunked_uploads/%Y/%m/%d"


class DBFSINANStorage(FileSystemStorage):
    """Storage for DBF SINAN uploads."""

    def __init__(self, location: str = "/DBF_SINAN", *args, **kwargs) -> None:
        super().__init__(location=location, *args, **kwargs)


CHUNKED_UPLOAD_STORAGE_CLASS = DBFSINANStorage


# URLs / WSGI
ROOT_URLCONF = "ad_main.urls"
WSGI_APPLICATION = "ad_main.wsgi.application"
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


# Databases
PSQL_DB = os.getenv("PSQL_DB")
PSQL_DBF = os.getenv("PSQL_DBF")
PSQL_USER = os.getenv("PSQL_USER")
PSQL_HOST = os.getenv("PSQL_HOST")
PSQL_PASSWORD = os.getenv("PSQL_PASSWORD")
PSQL_PORT = os.getenv("PSQL_PORT")

DATABASE_ROUTERS = ["manager.router.DatabaseAppsRouter"]
DATABASE_APPS_MAPPING = {
    "dados": "dados",
    "default": "default",
    "dbf": "infodengue",
    "forecast": "forecast",
}

DATABASES = {
    "dados": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": PSQL_DB,
        "USER": PSQL_USER,
        "PASSWORD": PSQL_PASSWORD,
        "HOST": PSQL_HOST,
        "PORT": PSQL_PORT,
    },
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": PSQL_DB,
        "USER": PSQL_USER,
        "PASSWORD": PSQL_PASSWORD,
        "HOST": PSQL_HOST,
        "PORT": PSQL_PORT,
    },
    "infodengue": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": PSQL_DBF,
        "USER": PSQL_USER,
        "PASSWORD": PSQL_PASSWORD,
        "HOST": PSQL_HOST,
        "PORT": PSQL_PORT,
    },
    "forecast": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": PSQL_DB,
        "USER": "forecast",
        "PASSWORD": PSQL_PASSWORD,
        "HOST": PSQL_HOST,
        "PORT": PSQL_PORT,
    },
}

MIGRATION_MODULES = {"dados": None, "gis": None, "api": None}
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"


# Security
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "SAMEORIGIN"
APPEND_SLASH = True


# Email
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
if EMAIL_BACKEND != "django.core.mail.backends.console.EmailBackend":
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = os.getenv("EMAIL_PORT")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = True

EMAIL_CONNECTIONS = {
    "gmail": {
        "host": "smtp.gmail.com",
        "username": os.getenv("EMAIL_HOST_USER"),
        "password": os.getenv("EMAIL_HOST_PASSWORD"),
        "port": os.getenv("EMAIL_PORT"),
        "use_tls": False,
    },
    "outlook": {
        "host": "imap-mail.outlook.com",
        "username": os.getenv("EMAIL_OUTLOOK_USER"),
        "password": os.getenv("EMAIL_OUTLOOK_PASSWORD"),
        "port": os.getenv("EMAIL_PORT"),
        "use_tls": True,
    },
    "ses": {"backend": "django_ses.SESBackend"},
}
EMAIL_CONNECTION_DEFAULT = os.getenv("EMAIL_CONNECTION_DEFAULT")
EMAIL_FROM_USER = os.getenv("EMAIL_FROM_USER")
EMAIL_TO_ADDRESS = os.getenv("EMAIL_TO_ADDRESS")
EMAIL_OUTLOOK_USER = os.getenv("EMAIL_OUTLOOK_USER")


# Static / Media
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
STATIC_URL = "/static/"
STATICFILES_DIRS = [str(APPS_DIR / "static")]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_URL = "/img/"
DBF_SINAN = os.getenv("DBF_SINAN")
MEDIA_ROOT = os.getenv("MEDIA_ROOT")
IMPORTED_FILES = os.getenv("IMPORTED_FILES")
TEMP_FILES_DIR = os.getenv("TEMP_FILES_DIR")
DATA_DIR = APPS_DIR.parent.parent / os.getenv("STORAGE", "")

if DEBUG:
    STATICFILES_STORAGE = (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
    )


# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(APPS_DIR / "templates")],
        "APP_DIRS": True,  # keep this in DEBUG
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "maintenance_mode.context_processors.maintenance_mode",
            ],
        },
    }
]

if DEBUG:
    # No custom loaders in DEBUG, so hot-reload works.
    TEMPLATES[0]["OPTIONS"]["debug"] = True
else:
    # In production, switch to cached loader.
    TEMPLATES[0]["APP_DIRS"] = False
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        (
            "django.template.loaders.cached.Loader",
            [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        )
    ]


# Paths to external services / data
MAPSERVER_URL = os.getenv("MAPSERVER_URL")
MAPSERVER_LOG_PATH = os.getenv("MAPSERVER_LOG_PATH")
SHAPEFILE_PATH = os.getenv("SHAPEFILE_PATH")
MAPFILE_PATH = os.getenv("MAPFILE_PATH")
RASTER_PATH = os.getenv("RASTER_PATH")

RASTER_METEROLOGICAL_DATA_RANGE = {
    "ndvi": (-2000.0, +10000.0),
    "lst_day_1km": (0.0, 20000.0),
    "lst_night_1km": (-30.0, 30.0),
    "relative_humidity_2m_above_ground": (0.0, 100.0),
    "specific_humidity_2m_above_ground": (0.0, 1.0),
    "precipitation": (0, 200.0),
}
RASTER_METEROLOGICAL_FACTOR_INCREASE = os.getenv(
    "RASTER_METEROLOGICAL_FACTOR_INCREASE"
)


# Caches
MEMCACHED_HOST = os.getenv("MEMCACHED_HOST")
MEMCACHED_PORT = os.getenv("MEMCACHED_PORT")
QUERY_CACHE_TIMEOUT = int(os.getenv("QUERY_CACHE_TIMEOUT", "600"))
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = "_"

if DEBUG:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    }
else:
    CACHES = {
        "default": {
            "BACKEND": (
                "django.core.cache.backends.memcached.PyMemcacheCache"
            ),
            "LOCATION": f"{MEMCACHED_HOST}:{MEMCACHED_PORT}",
            "OPTIONS": {
                "no_delay": True,
                "ignore_exc": True,
                "max_pool_size": 4,
                "use_pooling": True,
            },
        }
    }


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "null": {"class": "logging.NullHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        }
    },
}


# Celery
broker_url = os.getenv("CELERY_BROKER_URL")
broker_connection_retry = True
broker_connection_retry_on_startup = True
task_always_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() == "true"
accept_content = ["json"]
task_serializer = "json"

if DEBUG:
    # Use django-db in dev to avoid external cache coupling.
    result_backend = "django-db"
else:
    result_backend = f"cache+memcached://{MEMCACHED_HOST}:{MEMCACHED_PORT}/"


# Bootstrap4
BOOTSTRAP4 = {
    "form_renderers": {
        "default": "dbf.forms.FormRendererWithHiddenFieldErrors"
    }
}


# Leaflet
LEAFLET_CONFIG = {
    "DEFAULT_CENTER": (-22.907000, -43.431000),
    "DEFAULT_ZOOM": 8,
    "MAXIMUM_ZOOM": 13,
    "TILES": "http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "MINIMAP": False,
    "ATTRIBUTION_PREFIX": (
        "Fonte: <a href=http://info.dengue.mat.br>info.dengue.mat.br</a>"
    ),
    "PLUGINS": {
        "cluster": {
            "js": "js/leaflet.markercluster.js",
            "css": [
                "css/MarkerCluster.Default.css",
                "css/MarkerCluster.css",
            ],
            "auto-include": True,
        },
        "heatmap": {
            "js": [
                "libs/heatmap/heatmap.js",
                "libs/heatmap/leaflet-heatmap.js",
                "js/QuadTree.js",
            ]
        },
    },
    "RESET_VIEW": False,
}


# MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")


# Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN", default=None)
if SENTRY_DSN:
    sentry_sdk.init(
        SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=True,
    )
