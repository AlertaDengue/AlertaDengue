"""
Base Django settings for the AlertaDengue project.

This module contains configuration shared by all environments. Environment-
specific overrides live in ``dev.py`` and ``prod.py``.
"""


from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, TypeVar

import ibis
import pandas as pd
import psycopg2
from django.conf import settings
from django.contrib.messages import constants as messages
from django.core.files.storage import FileSystemStorage
from dotenv import load_dotenv
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.django import DjangoIntegration
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()
env_path = Path(".") / ".envs/.env"
load_dotenv(dotenv_path=env_path)


def read_admins(value: str) -> tuple[tuple[str, str], ...]:
    """Parse ADMINS environment variable.

    Parameters
    ----------
    value : str
        Comma-separated list of entries in the form ``name:email``.

    Returns
    -------
    tuple of tuple of str
        Parsed admins in Django's expected format.
    """
    if not value:
        return tuple()

    pairs: list[tuple[str, str]] = []
    for item in value.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        if ":" in cleaned:
            name, email = cleaned.split(":", 1)
            pairs.append((name.strip(), email.strip()))
    return tuple(pairs)


# /opt/services/AlertaDengue/ad_main/settings/base.py
# parent.parent.parent.parent == /opt/services
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent.parent
# APP_DIRS = BASE_DIR / "AlertaDengue"
PROJECT_ROOT = BASE_DIR / "AlertaDengue"

SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = (
    os.getenv("ALLOWED_HOSTS").split(",") if os.getenv("ALLOWED_HOSTS") else []
)
ADMINS = read_admins(os.getenv("ADMINS", ""))

MAINTENANCE_MODE = os.getenv("MAINTENANCE", "False").lower() == "true"
MAINTENANCE_MODE_TEMPLATE = str(PROJECT_ROOT / "dados/templates/503.html")

TIME_ZONE = "America/Sao_Paulo"
LANGUAGE_CODE = "pt-br"
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [str(PROJECT_ROOT / "locale")]
LANGUAGES = (
    ("pt-br", "Português"),
    ("en-us", "English"),
    ("es", "Spanish"),
)

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
    "pwa",
]

LOCAL_APPS = [
    "dados",
    "gis",
    "forecast",
    "dbf.apps.DbfConfig",
    "api",
    "upload",
    "ingestion",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

BASE_MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "maintenance_mode.middleware.MaintenanceModeMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

MESSAGE_TAGS = {
    messages.DEBUG: "alert-secondary",
    messages.INFO: "alert-info",
    messages.SUCCESS: "alert-success",
    messages.WARNING: "alert-warning",
    messages.ERROR: "alert-danger",
}

CHUNKED_UPLOAD_PATH = "uploaded/chunked_uploads/%Y/%m/%d"


class DBFSINANStorage(FileSystemStorage):
    """Storage backend for DBF SINAN uploads."""

    def __init__(self, location: str = "/DBF_SINAN", *args, **kwargs) -> None:
        super().__init__(location=location, *args, **kwargs)


CHUNKED_UPLOAD_STORAGE_CLASS = DBFSINANStorage

ROOT_URLCONF = "ad_main.urls"
WSGI_APPLICATION = "ad_main.wsgi.application"
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

T = TypeVar("T")
_IBIS_LOCAL = threading.local()

PSQL_HOST: str = os.getenv("PSQL_HOST", "postgres")
PSQL_PORT: int = int(os.getenv("PSQL_PORT", "5432"))
PSQL_DB: str = os.getenv("PSQL_DB", "dengue")
PSQL_USER: str = os.getenv("PSQL_USER", "dengueadmin")
PSQL_PASSWORD: str = os.getenv("PSQL_PASSWORD", "dengueadmin")
PSQL_DBF: str = os.getenv("PSQL_DBF", "infodengue")


def _with_ibis_retry(fn: Callable[[], T]) -> T:  # pragma: no cover
    """Execute an Ibis operation with a single reconnect retry."""
    try:
        return fn()
    except psycopg2.InterfaceError:
        if hasattr(_IBIS_LOCAL, "backend"):
            _IBIS_LOCAL.backend = None
        return fn()


def get_sqla_conn(psql_db: Optional[str] = None) -> Engine:
    """Create SQLAlchemy engine for a PostgreSQL database."""
    db_name = psql_db or PSQL_DB
    dsn = (
        f"postgresql+psycopg2://{PSQL_USER}:{PSQL_PASSWORD}"
        f"@{PSQL_HOST}:{PSQL_PORT}/{db_name}"
    )
    return create_engine(dsn, pool_pre_ping=True, future=True)


def get_ibis_conn() -> ibis.backends.postgres.Backend:
    """Return a per-thread Ibis Postgres backend, recreating it if stale."""
    backend = getattr(_IBIS_LOCAL, "backend", None)

    if backend is not None:
        try:
            backend.raw_sql("SELECT 1")
            return backend
        except Exception:
            _IBIS_LOCAL.backend = None

    backend = ibis.postgres.connect(
        user=PSQL_USER,
        password=PSQL_PASSWORD,
        host=PSQL_HOST,
        port=PSQL_PORT,
        database=PSQL_DB,
    )
    _IBIS_LOCAL.backend = backend
    return backend


def ibis_table(
    name: str,
    *,
    database: str | None = None,
) -> ibis.expr.types.relations.Table:
    """Return an Ibis table expression."""
    con = get_ibis_conn()
    if database is None:
        return con.table(name)
    return con.table(name, database=database)


DB_ENGINE: Engine = get_sqla_conn()
DB_ENGINE_FACTORY = get_sqla_conn

IBIS_CONN_FACTORY = get_ibis_conn
IBIS_TABLE = ibis_table

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

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "SAMEORIGIN"
APPEND_SLASH = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    "https://info.dengue.mat.br",
]
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

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

STATIC_ROOT = str(BASE_DIR / "staticfiles")
STATIC_URL = "/static/"

STATICFILES_DIRS = [str(PROJECT_ROOT / "static")]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_URL = "/img/"
DBF_SINAN = os.getenv("DBF_SINAN")
MEDIA_ROOT = os.getenv("MEDIA_ROOT")
IMPORTED_FILES = os.getenv("IMPORTED_FILES")
TEMP_FILES_DIR = os.getenv("TEMP_FILES_DIR")
DATA_DIR = PROJECT_ROOT.parent.parent / os.getenv("STORAGE", "")


def build_templates(debug: bool) -> list[dict[str, Any]]:
    """Build Django TEMPLATES configuration.

    Parameters
    ----------
    debug : bool
        Flag indicating whether the environment is a debug environment.

    Returns
    -------
    list of dict
        Template backend configuration.
    """
    base_options: dict[str, Any] = {
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
    }

    config: dict[str, Any] = {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # main change: use project root templates dir
        "DIRS": [str(PROJECT_ROOT / "templates")],
        "APP_DIRS": True,
        "OPTIONS": base_options,
    }

    if debug:
        config["OPTIONS"]["debug"] = True
    else:
        config["APP_DIRS"] = False
        config["OPTIONS"]["loaders"] = [
            (
                "django.template.loaders.cached.Loader",
                [
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ],
            )
        ]

    return [config]


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
    "precipitation": (0.0, 200.0),
}
RASTER_METEROLOGICAL_FACTOR_INCREASE = os.getenv(
    "RASTER_METEROLOGICAL_FACTOR_INCREASE"
)

MEMCACHED_HOST = os.getenv("MEMCACHED_HOST")
MEMCACHED_PORT = os.getenv("MEMCACHED_PORT")
QUERY_CACHE_TIMEOUT = int(os.getenv("QUERY_CACHE_TIMEOUT", "600"))
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = "_"


def build_caches(debug: bool) -> dict[str, Any]:
    """Build Django CACHES configuration.

    Parameters
    ----------
    debug : bool
        Flag indicating whether the environment is a debug environment.

    Returns
    -------
    dict
        Cache backend configuration.
    """
    if debug:
        return {
            "default": {
                "BACKEND": ("django.core.cache.backends.dummy.DummyCache")
            }
        }

    location = f"{MEMCACHED_HOST}:{MEMCACHED_PORT}"
    return {
        "default": {
            "BACKEND": (
                "django.core.cache.backends.memcached.PyMemcacheCache"
            ),
            "LOCATION": location,
            "OPTIONS": {
                "no_delay": True,
                "ignore_exc": True,
                "max_pool_size": 4,
                "use_pooling": True,
            },
        }
    }


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

broker_url = os.getenv("CELERY_BROKER_URL")
broker_connection_retry = True
broker_connection_retry_on_startup = True
task_always_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() == "true"
accept_content = ["json"]
task_serializer = "json"


def build_result_backend(debug: bool) -> str:
    """Build Celery result backend URL.

    Parameters
    ----------
    debug : bool
        Flag indicating whether the environment is a debug environment.

    Returns
    -------
    str
        Celery result backend DSN.
    """
    if debug:
        return "django-db"
    return f"cache+memcached://{MEMCACHED_HOST}:{MEMCACHED_PORT}/"


BOOTSTRAP4 = {
    "form_renderers": {
        "default": "dbf.forms.FormRendererWithHiddenFieldErrors"
    }
}

LEAFLET_CONFIG = {
    "DEFAULT_CENTER": (-22.907000, -43.431000),
    "DEFAULT_ZOOM": 8,
    "MAXIMUM_ZOOM": 13,
    "TILES": ("http://{s}.basemaps.cartocdn.com/" "light_all/{z}/{x}/{y}.png"),
    "MINIMAP": False,
    "ATTRIBUTION_PREFIX": (
        "Fonte: <a href=http://info.dengue.mat.br>" "info.dengue.mat.br</a>"
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

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")

SENTRY_DSN = os.getenv("SENTRY_DSN", default=None)
if SENTRY_DSN:
    sentry_init(
        SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=True,
    )

PWA_APP_NAME = (
    "InfoDengue – Early warning system for arbovirus transmission "
    "(dengue, chikungunya, and Zika)"
)
PWA_APP_SHORT_NAME = "InfoDengue"
PWA_APP_DESCRIPTION = (
    "InfoDengue data portal for monitoring arbovirus transmission."
)
PWA_APP_LANG = LANGUAGE_CODE
PWA_APP_DIR = "ltr"
PWA_APP_DISPLAY = "standalone"
PWA_APP_START_URL = "/"
PWA_APP_THEME_COLOR = "#0080ff"
PWA_APP_BACKGROUND_COLOR = "#ffffff"

PWA_APP_ICONS = [
    {
        "src": "/static/img/logo-infodengue.png",
        "sizes": "192x192",
        "type": "image/png",
    },
    {
        "src": "/static/img/logo-infodengue.png",
        "sizes": "512x512",
        "type": "image/png",
    },
]

PWA_APP_SCOPE = "/"
PWA_APP_ORIENTATION = "portrait"
PWA_APP_STATUS_BAR_COLOR = "#469ad3"

PWA_SERVICE_WORKER_PATH = PROJECT_ROOT / "static" / "js" / "serviceworker.js"
PWA_APP_MANIFEST_FILE = PROJECT_ROOT / "templates" / "manifest.json"
