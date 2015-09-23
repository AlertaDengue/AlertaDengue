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
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ["alerta.dengue.mat.br", "info.dengue.mat.br"]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'leaflet',
    'bootstrap3',
    'debug_toolbar',
    'dados',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'AlertaDengue.urls'

TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

WSGI_APPLICATION = 'AlertaDengue.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': os.path.join(BASE_DIR, 'geodjango.db'),
    }
}

LEAFLET_CONFIG = {
    # 'SPATIAL_EXTENT': (),
    'DEFAULT_CENTER': (-22.907111, -43.431864),
    'DEFAULT_ZOOM': 11,
    'MAXIMUM_ZOOM': 13,
    'TILES': 'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',  # 'http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png',
    'MINIMAP': False,
    'ATTRIBUTION_PREFIX': 'Fonte: <a href=http://info.dengue.mat.br>info.dengue.mat.br</a>',
    'PLUGINS': {
        'cluster': {
            'js': 'js/leaflet.markercluster.js',
            'css': ['css/MarkerCluster.Default.css', 'css/MarkerCluster.css'],
            'auto-include': True
        },
        'heatmap': {
            'js': ['js/heatmap.js', 'js/heatmap-leaflet.js', 'js/QuadTree.js'],
        }
    }

}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
CURRENT_DIR = os.path.join(os.path.dirname(__file__), '..')

STATIC_ROOT = os.path.join(CURRENT_DIR, 'static_files')  # up one level from settings.py
STATICFILES_DIRS = (
    os.path.abspath(os.path.join(CURRENT_DIR, 'static')),  # static is on root level
)

DATA_DIR = os.path.abspath(os.path.join(CURRENT_DIR, 'data'))

STATIC_URL = '/static/'

# Not having this was causing errors when running the project under wsgi:
# https://stackoverflow.com/questions/20963856/improperlyconfigured-the-included-urlconf-project-urls-doesnt-have-any-patte/21005346#21005346
DEBUG_TOOLBAR_PATCH_SETTINGS = False

try:
    from AlertaDengue.local_settings import *
except ImportError:
    pass
