"""Pytest fixtures for dbdata tests."""

from __future__ import annotations

import pytest
from django.conf import settings
from sqlalchemy import text
from sqlalchemy.engine import Engine

TEST_SCHEMA = "test_views"
HIST_UF_VIEW = "hist_uf_dengue_materialized_view"


@pytest.fixture()
def db_engine() -> Engine:
    """Return the SQLAlchemy engine configured by Django settings."""
    return settings.DB_ENGINE


@pytest.fixture()
def hist_uf_dengue_table(db_engine: Engine) -> None:
    """Create a fake hist_uf_dengue_materialized_view in a test schema."""
    with db_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{TEST_SCHEMA}"'))
        conn.execute(
            text(f'DROP TABLE IF EXISTS "{TEST_SCHEMA}".{HIST_UF_VIEW}')
        )
        conn.execute(
            text(
                f"""
                CREATE TABLE "{TEST_SCHEMA}".{HIST_UF_VIEW} (
                    state_abbv TEXT NOT NULL,
                    "SE" INTEGER NOT NULL,
                    casos_est INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                f"""
                INSERT INTO "{TEST_SCHEMA}".{HIST_UF_VIEW}
                    (state_abbv, "SE", casos_est)
                VALUES
                    ('RJ', 10, 0),
                    ('RJ', 12, 1),
                    ('RJ', 11, 0),
                    ('SP',  1, 0)
                """
            )
        )

    yield

    with db_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
