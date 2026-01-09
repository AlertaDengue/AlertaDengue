from __future__ import annotations

import os

from celery import Celery

# Respect DJANGO_SETTINGS_MODULE if it is already set (by Docker).
# Otherwise default to dev.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "ad_main.settings.dev"),
)


app = Celery("ad_main", include=["dbf.tasks", "upload.tasks"])

# Load all CELERY_* settings from the Django settings module
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
