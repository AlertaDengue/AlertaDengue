"""Pytest bootstrap for Django initialization."""

from __future__ import annotations

import os

import django


def pytest_configure() -> None:
    """Initialize Django before test collection imports Django models."""
    from .test_utils import ensure_test_databases_exist

    ensure_test_databases_exist()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ad_main.settings.testing")
    os.environ.setdefault("PGOPTIONS", "-c search_path=test_views,public")
    django.setup()
