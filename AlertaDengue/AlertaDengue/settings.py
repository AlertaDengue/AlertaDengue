# coding=utf-8
"""
Django settings for AlertaDengue project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from decouple import config, Csv
from dj_database_url import parse as db_url


def read_admins(value):
    # ADMIN in settings.ini should be in the format:
    # admin 1, admin1@example.org; admin 2, admin2@example.org
    if value == '':
        return tuple()
    return tuple(tuple(v.split(',')) for v in value.split(';'))


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PARENT_BASE_DIR = os.path.dirname(BASE_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

ADMINS = config('ADMINS', cast=read_admins, default='')

ALLOWED_HOSTS = ["alerta.dengue.mat.br", "info.dengue.mat.br"]
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'leaflet',
    'bootstrap3',
    'chunked_upload',
    'dados',
    'gis',
    'forecast',
    'dbf.apps.DbfConfig',
    'api',
    'manager.router'
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

# django 2
MIDDLEWARE = MIDDLEWARE_CLASSES

ROOT_URLCONF = 'AlertaDengue.urls'

WSGI_APPLICATION = 'AlertaDengue.wsgi.application'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'DIRS': [os.path.join(BASE_DIR, 'templates')],
    'OPTIONS': {
        'context_processors': [
            "django.contrib.auth.context_processors.auth",
            "django.template.context_processors.debug",
            "django.template.context_processors.i18n",
            "django.template.context_processors.media",
            "django.template.context_processors.static",
            "django.template.context_processors.tz",
            "django.contrib.messages.context_processors.messages"
        ],
    }
}]

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': config(
        'DATABASE_URL', default='sqlite:///geodjango.db', cast=db_url
    )
}

MEMCACHED_HOST = config('MEMCACHED_HOST', '127.0.0.1')
MEMCACHED_PORT = config('MEMCACHED_PORT', '11211')
QUERY_CACHE_TIMEOUT = config('QUERY_CACHE_TIMEOUT', 60 * 60, cast=int)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '{}:{}'.format(MEMCACHED_HOST, MEMCACHED_PORT),
    }
}

LEAFLET_CONFIG = {
    # 'SPATIAL_EXTENT': (),
    'DEFAULT_CENTER': (-22.907000, -43.431000),
    'DEFAULT_ZOOM': 8,
    'MAXIMUM_ZOOM': 13,
    # 'http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png',
    'TILES': 'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    'MINIMAP': False,
    'ATTRIBUTION_PREFIX':
        'Fonte: <a href=http://info.dengue.mat.br>info.dengue.mat.br</a>',
    'PLUGINS': {
        'cluster': {
            'js': 'js/leaflet.markercluster.js',
            'css': ['css/MarkerCluster.Default.css', 'css/MarkerCluster.css'],
            'auto-include': True
        },
        'heatmap': {
            'js': [
                'libs/heatmap/heatmap.js',
                'libs/heatmap/leaflet-heatmap.js',
                'js/QuadTree.js'
            ],
        }
    },
    'RESET_VIEW': False
}

PSQL_DB = config('PSQL_DB', default="dengue")
PSQL_USER = config('PSQL_USER', default="dengueadmin")
PSQL_HOST = config('PSQL_HOST', default="localhost")
PSQL_PASSWORD = config('PSQL_PASSWORD')

DATABASE_ROUTERS = [
    'manager.router.DatabaseAppsRouter'
]
DATABASE_APPS_MAPPING = {
    'dados': 'dados',
    'forecast': 'forecast',
    'dbf': 'default'
}

DATABASES.update({
    'dados': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': PSQL_DB,
        'USER': PSQL_USER,
        'PASSWORD': PSQL_PASSWORD,
        'HOST': PSQL_HOST,
        'PORT': ''
    },
    'forecast': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': PSQL_DB,
        'USER': 'forecast',
        'PASSWORD': PSQL_PASSWORD,
        'HOST': PSQL_HOST,
        'PORT': ''
    }
})

MIGRATION_MODULES = {
    'dados': None,
    'gis': None,
    'api': None
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'pt-br'
LANGUAGES = (('pt-br', 'Português'),
             ('en-us', 'english'))

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]


APPEND_SLASH = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
CURRENT_DIR = os.path.join(os.path.dirname(__file__), '..')

# up one level from settings.py
STATIC_ROOT = os.path.join(CURRENT_DIR, 'static_files')
# static is on root level
STATICFILES_DIRS = (
    os.path.abspath(os.path.join(CURRENT_DIR, 'static')),
)

DATA_DIR = os.path.abspath(os.path.join(CURRENT_DIR, 'data'))

STATIC_URL = '/static/'

MEDIA_ROOT = config('MEDIA_ROOT', default='')

IMPORTED_FILES_DIR = config('IMPORTED_FILES_DIR', default=MEDIA_ROOT)

EMAIL_BACKEND = config(
    'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_FROM_ADDRESS = config(
    'EMAIL_FROM_ADDRESS', 'no-reply@info.dengue.mat.br'
)
INFODENGUE_TEAM_EMAIL = config('INFODENGUE_TEAM_EMAIL',
        'infodengue@info.dengue.mat.br')

if EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
    EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD = config(
        'EMAIL_CONFIG', default='example_host,25,username,password',
        cast=Csv()
    )
    EMAIL_PORT = int(EMAIL_PORT)
    EMAIL_USE_TLS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
    },
}


CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=None)
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False)

MAPSERVER_URL = config(
    'MAPSERVER_URL', default='http://localhost:80'
)

MAPSERVER_LOG_PATH = config(
    'MAPSERVER_LOG_PATH', default='/var/log/mapserver.log'
)


SHAPEFILE_PATH = '%s/static/shapefile' % BASE_DIR
MAPFILE_PATH = config(
    'MAPFILE_PATH', default='%s/mapfiles' % PARENT_BASE_DIR
)

RASTER_PATH = config(
    'RASTER_PATH', default=os.path.join(PARENT_BASE_DIR, 'tiffs')
)

RASTER_METEROLOGICAL_DATA_RANGE = {
    'ndvi': (-2000.0, +10000.0),
    'lst_day_1km': (0.0, 20000.0),
    'lst_night_1km': (-30.0, 30.0),
    'relative_humidity_2m_above_ground': (0.0, 100.0),
    'specific_humidity_2m_above_ground': (0.0, 1.0),
    'precipitation': (0, 200.0)
}

RASTER_METEROLOGICAL_FACTOR_INCREASE = config(
    'RASTER_METEROLOGICAL_FACTOR_INCREASE', default=4
)

BOOTSTRAP3 = {
    'form_renderers': {
        'default': 'dbf.forms.FormRendererWithHiddenFieldErrors',
    }
}

try:
    from .local_settings import *
except ImportError:
    pass
