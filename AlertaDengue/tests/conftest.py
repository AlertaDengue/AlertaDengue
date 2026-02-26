from __future__ import annotations

import os

import django


def pytest_configure(config) -> None:
    """
    Configure Django initialization for tests.

    If pytest-django is available, it will handle django.setup() and DB setup.
    If not, we fallback to calling django.setup() so importing models works.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ad_main.settings.testing")
    os.environ.setdefault("PGOPTIONS", "-c search_path=test_views,public")

    config.addinivalue_line(
        "markers",
        "django_db: uses the Django database",
    )

    if not config.pluginmanager.hasplugin("django"):
        django.setup()
