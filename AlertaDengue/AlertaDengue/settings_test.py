# coding=utf-8
"""
Django settings for AlertaDengue project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

from .settings import *  # noqa: F403 F401


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
    'AlertaDengue.dados',
    'AlertaDengue.gis',
    'AlertaDengue.forecast',
    'AlertaDengue.dbf.apps.DbfConfig',
    'AlertaDengue.api',
    'AlertaDengue.manager.router',
)

DATABASE_ROUTERS = ['AlertaDengue.manager.router.DatabaseAppsRouter']
DATABASE_APPS_MAPPING = {
    'dados': 'dados',
    'forecast': 'forecast',
    'dbf': 'default',
}

MIGRATION_MODULES = {'dados': None, 'gis': None, 'api': None}
