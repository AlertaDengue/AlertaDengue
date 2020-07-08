"""
Django settings for AlertaDengue project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from dotenv import load_dotenv
from os.path import join, dirname

env_file = os.environ.get('ENV_FILE', '.env')

dotenv_path = join(dirname(dirname(dirname(__file__))), env_file)
load_dotenv(dotenv_path)


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
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', '').lower() == 'true'

# if True the maintenance-mode will be activated
MAINTENANCE_MODE = None

# You must set settings.ALLOWED_HOSTS if DEBUG is False.
ADMINS = tuple(v.split(':') for v in os.getenv('ADMINS').split(','))

# ALLOWED_HOSTS=os.getenv["alerta.dengue.mat.br",
# "info.dengue.mat.br", '127.0.0.1'] ###VERIFICAR EM .ENV
ALLOWED_HOSTS = (
    os.getenv('ALLOWED_HOSTS').split(',') if os.getenv('ALLOWED_HOSTS') else []
)


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
    'bootstrap4',
    'chunked_upload',
    'dados',
    'gis',
    'forecast',
    'dbf.apps.DbfConfig',
    'api',
    'manager.router',
    'maintenance_mode',
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
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
)

# django 2
MIDDLEWARE = MIDDLEWARE_CLASSES

ROOT_URLCONF = 'ad_main.urls'

WSGI_APPLICATION = 'ad_main.wsgi.application'

TEMPLATES = [
    {
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
                "django.contrib.messages.context_processors.messages",
                "maintenance_mode.context_processors.maintenance_mode",
            ]
        },
    }
]

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

PSQL_DB = os.getenv('PSQL_DB')
PSQL_DBF = os.getenv('PSQL_DBF')
PSQL_USER = os.getenv('PSQL_USER')
PSQL_HOST = os.getenv('PSQL_HOST')
PSQL_PASSWORD = os.getenv('PSQL_PASSWORD')
PSQL_PORT = os.getenv('PSQL_PORT')

DATABASE_ROUTERS = ['manager.router.DatabaseAppsRouter']
DATABASE_APPS_MAPPING = {
    'dados': 'dados',
    'default': 'default',
    'dbf': 'infodengue',
    'forecast': 'forecast',
}

DATABASES = {
    'dados': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': PSQL_DB,
        'USER': PSQL_USER,
        'PASSWORD': PSQL_PASSWORD,
        'HOST': PSQL_HOST,
        'PORT': PSQL_PORT,
    },
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': PSQL_DB,
        'USER': PSQL_USER,
        'PASSWORD': PSQL_PASSWORD,
        'HOST': PSQL_HOST,
        'PORT': PSQL_PORT,
    },
    'infodengue': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': PSQL_DBF,
        'USER': PSQL_USER,
        'PASSWORD': PSQL_PASSWORD,
        'HOST': PSQL_HOST,
        'PORT': PSQL_PORT,
    },
    'forecast': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': PSQL_DB,
        'USER': 'forecast',
        'PASSWORD': PSQL_PASSWORD,
        'HOST': PSQL_HOST,
        'PORT': PSQL_PORT,
    },
}


MEMCACHED_HOST = os.getenv('MEMCACHED_HOST')
MEMCACHED_PORT = os.getenv('MEMCACHED_PORT')
QUERY_CACHE_TIMEOUT = 60 * 60

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
    'ATTRIBUTION_PREFIX': (
        'Fonte: <a href=http://info.dengue.mat.br>info.dengue.mat.br</a>'
    ),
    'PLUGINS': {
        'cluster': {
            'js': 'js/leaflet.markercluster.js',
            'css': ['css/MarkerCluster.Default.css', 'css/MarkerCluster.css'],
            'auto-include': True,
        },
        'heatmap': {
            'js': [
                'libs/heatmap/heatmap.js',
                'libs/heatmap/leaflet-heatmap.js',
                'js/QuadTree.js',
            ]
        },
    },
    'RESET_VIEW': False,
}

MIGRATION_MODULES = {'dados': None, 'gis': None, 'api': None}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'pt-br'
LANGUAGES = (('pt-br', 'Português'), ('en-us', 'english'), ('es', 'Spanish'))

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]

APPEND_SLASH = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
CURRENT_DIR = os.path.join(dirname(dirname(__file__)))


# up one level from settings.py
STATIC_ROOT = os.path.join(CURRENT_DIR, 'static_files')
# static is on root level
STATICFILES_DIRS = (os.path.abspath(os.path.join(CURRENT_DIR, 'static')),)

DATA_DIR = os.path.abspath(os.path.join(CURRENT_DIR, 'data'))

STATIC_URL = '/static/'

MAINTENANCE_MODE_TEMPLATE = '%s/dados/templates/503.html' % BASE_DIR

MEDIA_ROOT = os.getenv('MEDIA_ROOT')

IMPORTED_FILES_DIR = os.getenv('IMPORTED_FILES_DIR')

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND')

EMAIL_FROM_ADDRESS = os.getenv('EMAIL_FROM_ADDRESS')

INFODENGUE_TEAM_EMAIL = os.getenv('INFODENGUE_TEAM_EMAIL')

if EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
    EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD = (
        os.getenv('EMAIL_CONFIG')
    ).split(',')
    EMAIL_PORT = int(EMAIL_PORT)
    EMAIL_USE_TLS = True


CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')  # Verificar ERROR CELERY
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER')

MAPSERVER_URL = os.getenv('MAPSERVER_URL')

MAPSERVER_LOG_PATH = os.getenv('MAPSERVER_LOG_PATH')


SHAPEFILE_PATH = os.getenv('SHAPEFILE_PATH')
MAPFILE_PATH = os.getenv('MAPFILE_PATH')

RASTER_PATH = os.getenv(
    'RASTER_PATH'
)  # , default=os.path.join(PARENT_BASE_DIR, 'tiffs'


RASTER_METEROLOGICAL_DATA_RANGE = {
    'ndvi': (-2000.0, +10000.0),
    'lst_day_1km': (0.0, 20000.0),
    'lst_night_1km': (-30.0, 30.0),
    'relative_humidity_2m_above_ground': (0.0, 100.0),
    'specific_humidity_2m_above_ground': (0.0, 1.0),
    'precipitation': (0, 200.0),
}

RASTER_METEROLOGICAL_FACTOR_INCREASE = os.getenv(
    'RASTER_METEROLOGICAL_FACTOR_INCREASE'
)  # VERIFICAR , default=4

BOOTSTRAP4 = {
    'form_renderers': {
        'default': 'dbf.forms.FormRendererWithHiddenFieldErrors'
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
        'null': {'class': 'logging.NullHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        }
    },
}
