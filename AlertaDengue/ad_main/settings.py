"""
Django settings for AlertaDengue project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# using existing module to specify location of the .env file
load_dotenv()
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)


def read_admins(value):
    # ADMIN in settings.ini should be in the format:
    # admin 1, admin1@example.org; admin 2, admin2@example.org
    if value == "":
        return tuple()
    return tuple(tuple(v.split(",")) for v in value.split(";"))


BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
PARENT_BASE_DIR = Path(BASE_DIR)
# Storage destination path between production and development are not the same
DATA_DIR = PARENT_BASE_DIR.parent.parent / os.getenv("STORAGE")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "").lower() == "true"

# if True the maintenance-mode will be activated
MAINTENANCE_MODE = None

# You must set settings.ALLOWED_HOSTS if DEBUG is False
ADMINS = tuple(v.split(":") for v in os.getenv("ADMINS").split(","))

# ALLOWED_HOSTS=os.getenv["alerta.dengue.mat.br",
# "info.dengue.mat.br", '127.0.0.1'] ###VERIFICAR EM .ENV
ALLOWED_HOSTS = (
    os.getenv("ALLOWED_HOSTS").split(",") if os.getenv("ALLOWED_HOSTS") else []
)

# Application definition
INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "leaflet",
    "bootstrap4",
    "chunked_upload",
    "dados",
    "gis",
    "forecast",
    "dbf.apps.DbfConfig",
    "api",
    "manager.router",
    "maintenance_mode",
)

if DEBUG:
    INSTALLED_APPS += ("django_extensions",)

MIDDLEWARE_CLASSES = (
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.cache.UpdateCacheMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.cache.FetchFromCacheMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "maintenance_mode.middleware.MaintenanceModeMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
)

if DEBUG:
    MIDDLEWARE_CLASSES += (
        "django_cprofile_middleware.middleware.ProfilerMiddleware",
    )
    DJANGO_CPROFILE_MIDDLEWARE_REQUIRE_STAFF = False

MIDDLEWARE = MIDDLEWARE_CLASSES
ROOT_URLCONF = "ad_main.urls"
WSGI_APPLICATION = "ad_main.wsgi.application"
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [os.path.join(BASE_DIR, "templates")],
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
            ]
        },
    }
]

# Database
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

# Console backend writes to stdout.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND")
if EMAIL_BACKEND != "django.core.mail.backends.console.EmailBackend":
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = os.getenv("EMAIL_PORT")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = True

# SEND_MAIL DBF
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

# Uses the same credentials from email backend
EMAIL_FROM_USER = os.getenv("EMAIL_FROM_USER")
EMAIL_TO_ADDRESS = os.getenv("EMAIL_TO_ADDRESS")
EMAIL_OUTLOOK_USER = os.getenv("EMAIL_OUTLOOK_USER")

# URL to use when referring to static files located in STATIC_ROOT.
STATIC_URL = "/static/"

# TODO: up one level from settings.py
# collectstatic will collect static files for deployment.
STATIC_ROOT = PARENT_BASE_DIR / "static_files"

# django will look for static files
STATICFILES_DIRS = [
    PARENT_BASE_DIR / "static",
    # Collect files from Storage
    *[str(f) for f in list(DATA_DIR.glob("**/*data"))],
]
# used to upload dbf
MEDIA_ROOT = os.getenv("MEDIA_ROOT")
IMPORTED_FILES_DIR = os.getenv("IMPORTED_FILES_DIR")
TEMP_FILES_DIR = os.getenv("TEMP_FILES_DIR")

MAPSERVER_URL = os.getenv("MAPSERVER_URL")
MAPSERVER_LOG_PATH = os.getenv("MAPSERVER_LOG_PATH")

SHAPEFILE_PATH = os.getenv("SHAPEFILE_PATH")
MAPFILE_PATH = os.getenv("MAPFILE_PATH")

RASTER_PATH = os.getenv(
    "RASTER_PATH"
)  # , default=os.path.join(PARENT_BASE_DIR, 'tiffs'

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
)  # VERIFICAR , default=4

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")  # Verificar ERROR CELERY
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER")

MEMCACHED_HOST = os.getenv("MEMCACHED_HOST")
MEMCACHED_PORT = os.getenv("MEMCACHED_PORT")
QUERY_CACHE_TIMEOUT = int(os.getenv("QUERY_CACHE_TIMEOUT"))

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": f"{MEMCACHED_HOST}:{MEMCACHED_PORT}",
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

BOOTSTRAP4 = {
    "form_renderers": {
        "default": "dbf.forms.FormRendererWithHiddenFieldErrors"
    }
}


LEAFLET_CONFIG = {
    # 'SPATIAL_EXTENT': (),
    "DEFAULT_CENTER": (-22.907000, -43.431000),
    "DEFAULT_ZOOM": 8,
    "MAXIMUM_ZOOM": 13,
    # 'http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png',
    "TILES": "http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "MINIMAP": False,
    "ATTRIBUTION_PREFIX": (
        "Fonte: <a href=http://info.dengue.mat.br>info.dengue.mat.br</a>"
    ),
    "PLUGINS": {
        "cluster": {
            "js": "js/leaflet.markercluster.js",
            "css": ["css/MarkerCluster.Default.css", "css/MarkerCluster.css"],
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

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# ACTIVE_STATES = os.getenv('ACTIVE_STATES')
ACTIVE_STATES = (
    os.getenv("ACTIVE_STATES").split(",") if os.getenv("ACTIVE_STATES") else []
)

MAINTENANCE_MODE_TEMPLATE = "%s/dados/templates/503.html" % BASE_DIR

# HTTP security header
X_FRAME_OPTIONS = "SAMEORIGIN"

# HTTP redirect is issued to the same URL
APPEND_SLASH = True

# for translation files
LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]

# Internationalization
LANGUAGE_CODE = "pt-br"
LANGUAGES = (("pt-br", "Português"), ("en-us", "english"), ("es", "Spanish"))
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True
