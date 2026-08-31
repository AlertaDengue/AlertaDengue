"""PostgreSQL regression coverage for historical-alert tweet removal."""

from importlib import import_module

from django.db import ProgrammingError, connections, transaction
from django.db.migrations.state import ProjectState
import pytest

from manager.router import DatabaseAppsRouter

TABLES = (
    '"Municipio"."Historico_alerta"',
    '"Municipio"."Historico_alerta_chik"',
    '"Municipio"."Historico_alerta_zika"',
)
MIGRATION = import_module(
    "dados.migrations.0008_remove_historical_alert_tweet_column"
)


def apply_migration_operation(connection):
    """Run the actual Django migration operation on the ``dados`` alias."""
    operation = MIGRATION.Migration.operations[0]
    state = ProjectState()

    assert connection.alias == "dados"
    with connection.schema_editor() as schema_editor:
        operation.database_forwards(
            "dados", schema_editor, state, state.clone()
        )


@pytest.fixture
def disposable_historical_alert_tables():
    """Create only the disposable legacy tables required by this migration."""
    connection = connections["dados"]
    if connection.vendor != "postgresql":
        pytest.skip("the migration is PostgreSQL-specific")

    with connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA IF NOT EXISTS "Municipio"')
        for table in TABLES:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            cursor.execute(
                f"CREATE TABLE {table} ("
                "id integer PRIMARY KEY, preserved_value text NOT NULL, "
                '"tweet" numeric NULL DEFAULT NULL)'
            )
            cursor.execute(
                f'INSERT INTO {table} (id, preserved_value, "tweet") '
                "VALUES (1, 'retained', 1), (2, 'also-retained', NULL)"
            )
        cursor.execute(
            'CREATE TABLE "Municipio"."tweet_migration_sentinel" '
            "(id integer PRIMARY KEY, value text NOT NULL)"
        )
        cursor.execute(
            'INSERT INTO "Municipio"."tweet_migration_sentinel" '
            "VALUES (1, 'unchanged')"
        )

    yield connection

    with connection.cursor() as cursor:
        cursor.execute(
            'DROP TABLE IF EXISTS "Municipio"."tweet_migration_sentinel"'
        )
        for table in TABLES:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")


@pytest.mark.django_db(databases={"default", "dados"}, transaction=True)
def test_tweet_removal_migration_preserves_historical_alert_rows_and_columns(
    disposable_historical_alert_tables,
):
    """Apply the real migration SQL to disposable PostgreSQL tables."""
    connection = disposable_historical_alert_tables

    apply_migration_operation(connection)
    with connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'Municipio' AND table_name = %s "
                "ORDER BY ordinal_position",
                [table.split('"')[3]],
            )
            assert [row[0] for row in cursor.fetchall()] == [
                "id",
                "preserved_value",
            ]
            cursor.execute(
                f"SELECT id, preserved_value FROM {table} ORDER BY id"
            )
            assert cursor.fetchall() == [
                (1, "retained"),
                (2, "also-retained"),
            ]
        cursor.execute(
            'SELECT id, value FROM "Municipio"."tweet_migration_sentinel"'
        )
        assert cursor.fetchall() == [(1, "unchanged")]


@pytest.mark.django_db(databases={"default", "dados"}, transaction=True)
def test_tweet_removal_migration_is_atomic(disposable_historical_alert_tables):
    """A failed statement rolls back all three column removals."""
    connection = disposable_historical_alert_tables

    with pytest.raises(ProgrammingError), transaction.atomic(using="dados"):
        apply_migration_operation(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                'ALTER TABLE "Municipio"."missing" DROP COLUMN "tweet";'
            )

    with connection.cursor() as cursor:
        for table in TABLES:
            cursor.execute(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema = 'Municipio' AND table_name = %s "
                "AND column_name = 'tweet'",
                [table.split('"')[3]],
            )
            assert cursor.fetchone() == (1,)


def test_historical_alert_migration_is_routed_only_to_dados():
    """Django's router prevents this ``dados`` migration on ``default``."""
    router = DatabaseAppsRouter()

    assert router.allow_migrate("dados", "dados") is True
    assert router.allow_migrate("default", "dados") is False


def test_tweet_removal_migration_is_explicitly_irreversible():
    """The retired historical tweet values cannot be reconstructed."""
    assert MIGRATION.Migration.operations[0].reverse_sql is None
