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


@pytest.fixture()
def regional_parameters_tables(db_engine: Engine) -> None:
    """Create a fake Dengue_global schema and tables for RegionalParameters tests."""
    schema = "Dengue_global"
    with db_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

        # Drop tables if exist
        conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."parameters"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."Municipio"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."estado"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."regional"'))

        # Create tables
        # Municipio
        conn.execute(
            text(
                f"""
            CREATE TABLE "{schema}"."Municipio" (
                geocodigo BIGINT PRIMARY KEY,
                nome TEXT,
                uf TEXT,
                id_regional INTEGER
            )
        """
            )
        )

        # regional
        conn.execute(
            text(
                f"""
            CREATE TABLE "{schema}"."regional" (
                id INTEGER PRIMARY KEY,
                nome TEXT
            )
        """
            )
        )

        # parameters
        conn.execute(
            text(
                f"""
            CREATE TABLE "{schema}"."parameters" (
                id SERIAL PRIMARY KEY,
                municipio_geocodigo BIGINT,
                cid10 TEXT,
                codigo_estacao_wu TEXT,
                varcli TEXT,
                clicrit NUMERIC,
                varcli2 TEXT,
                clicrit2 NUMERIC,
                limiar_preseason NUMERIC,
                limiar_posseason NUMERIC,
                limiar_epidemico NUMERIC
            )
        """
            )
        )

        # Insert Mock Data
        # Regionals
        conn.execute(
            text(
                f"""
            INSERT INTO "{schema}"."regional" (id, nome) VALUES
            (1, 'Metropolitana I'),
            (2, 'Metropolitana II')
        """
            )
        )

        # Municipios
        # 3304557: Rio de Janeiro (Metro I)
        # 3303302: Niterói (Metro II)
        conn.execute(
            text(
                f"""
            INSERT INTO "{schema}"."Municipio" (geocodigo, nome, uf, id_regional) VALUES
            (3304557, 'Rio de Janeiro', 'RJ', 1),
            (3303302, 'Niterói', 'RJ', 2)
        """
            )
        )

        # Parameters
        # Dengue (A90) for Rio
        # Chik (A92.0) for Niterói
        conn.execute(
            text(
                f"""
            INSERT INTO "{schema}"."parameters" 
            (municipio_geocodigo, cid10, codigo_estacao_wu, varcli, clicrit, varcli2, clicrit2, 
             limiar_preseason, limiar_posseason, limiar_epidemico)
            VALUES
            (3304557, 'A90', '83743', 'p_rt1', 0.5, 'temp_min', 22.0, 100, 80, 300),
            (3303302, 'A92.0', '83000', 'p_rt1', 0.6, 'temp_min', 23.0, 50, 40, 150)
        """
            )
        )

    yield

    with db_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
