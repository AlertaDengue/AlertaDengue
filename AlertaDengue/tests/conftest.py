from __future__ import annotations

import os

import django
from django.conf import settings
import pytest
from sqlalchemy.engine import Engine


@pytest.fixture()
def db_engine() -> Engine:
    """Return the SQLAlchemy engine configured by Django settings."""
    return getattr(settings, "DB_ENGINE")


def pytest_configure(config) -> None:
    """
    Configure Django initialization for tests.

    If pytest-django is available, it will handle django.setup() and DB setup.
    If not, we fallback to calling django.setup() so importing models works.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ad_main.settings.testing")
    os.environ.setdefault("PGOPTIONS", "-c search_path=test_views,public")
    os.environ.setdefault("PSQL_HOST", "localhost")

    config.addinivalue_line(
        "markers",
        "django_db: uses the Django database",
    )

    if not config.pluginmanager.hasplugin("django"):
        django.setup()
