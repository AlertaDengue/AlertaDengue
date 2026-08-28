"""PostgreSQL fixtures shared by internal API tests."""

from pathlib import Path

from django.db import connections
import pytest

NOTIFICATION_SQL_FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "datasets"
    / "test_notification.output.sql"
)


@pytest.fixture()
def notification_table():
    """Provision the external notification schema on the ``dados`` alias."""
    database_connection = connections["dados"]
    if database_connection.vendor != "postgresql":
        pytest.skip(
            "notification adapters use PostgreSQL schema-qualified tables"
        )

    with database_connection.cursor() as cursor:
        cursor.execute(NOTIFICATION_SQL_FIXTURE.read_text(encoding="utf-8"))

    yield

    with database_connection.cursor() as cursor:
        cursor.execute(
            'DROP TABLE IF EXISTS "Municipio"."Notificacao" CASCADE'
        )
