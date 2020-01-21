#-*- coding: utf-8 -*-
# absolute_import makes shure this module won't clash with the library
from __future__ import absolute_import, unicode_literals
import os

from celery import Celery

# This makes sure celery knows where settings are, so we don't need to set it
# when calling it from the command line
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AlertaDengue.settings")

app = Celery("AlertaDengue")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
