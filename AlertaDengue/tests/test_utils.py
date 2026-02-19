"""Utilities for testing AlertaDengue."""

from __future__ import annotations

import os
from logging import getLogger

import psycopg2

logger = getLogger(__name__)


def ensure_test_databases_exist() -> None:
    """Ensure that the test databases exist in PostgreSQL."""
    psql_db = os.getenv("PSQL_DB", "dengue")
    psql_dbf = os.getenv("PSQL_DBF", "infodengue")

    databases_to_check = set()
    for db in [psql_db, psql_dbf]:
        if not db.startswith("test_"):
            databases_to_check.add(f"test_{db}")
        else:
            databases_to_check.add(db)

    user = os.getenv("PSQL_USER", "dengueadmin")
    password = os.getenv("PSQL_PASSWORD", "dengueadmin")
    host = os.getenv("POSTGRES_HOST") or os.getenv("PSQL_HOST") or "localhost"
    port = os.getenv("PSQL_PORT", "5432")

    try:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database="postgres",
        )
        conn.autocommit = True
        cur = conn.cursor()

        for db_name in databases_to_check:
            cur.execute(
                "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                (db_name,),
            )
            exists = cur.fetchone()

            if not exists:
                logger.info(f"Creating test database: {db_name}")
                cur.execute(f'CREATE DATABASE "{db_name}"')
            else:
                pass

        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Error ensuring test databases exist: {e}")
