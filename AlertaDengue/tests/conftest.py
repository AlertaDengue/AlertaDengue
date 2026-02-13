"""Pytest bootstrap for Django initialization."""

from __future__ import annotations

import os

import django


def pytest_configure() -> None:
    """Initialize Django before test collection imports Django models."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ad_main.settings.testing")
    os.environ.setdefault("PGOPTIONS", "-c search_path=test_views,public")
    django.setup()
