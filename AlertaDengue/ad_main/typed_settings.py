from __future__ import annotations

from pathlib import Path
from typing import Protocol, cast

from django.conf import settings
from sqlalchemy.engine import Engine


class _TypedSettings(Protocol):
    DB_ENGINE: Engine
    DATABASE_APPS_MAPPING: dict[str, str]
    QUERY_CACHE_TIMEOUT: int
    PROJECT_ROOT: Path
    TECHNICAL_REPORTS_ROOT: Path


typed_settings = cast(_TypedSettings, settings)


def get_db_engine() -> Engine:
    return typed_settings.DB_ENGINE


def get_database_apps_mapping() -> dict[str, str]:
    return typed_settings.DATABASE_APPS_MAPPING


def get_query_cache_timeout() -> int:
    return typed_settings.QUERY_CACHE_TIMEOUT


def get_project_root() -> Path:
    return typed_settings.PROJECT_ROOT


def get_technical_reports_root() -> Path:
    return typed_settings.TECHNICAL_REPORTS_ROOT
