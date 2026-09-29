from __future__ import annotations

from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import (
    IntegrityError,
    OperationalError,
    connections,
    transaction,
)
import pytest

from ingestion.management.commands.fix_notification_geocodes import Command
from ingestion.utils import EXCEPTIONAL_GEOCODE_CORRECTIONS, add_dv

# Explicit expectations guard the official mapping independently of its source.
OFFICIAL_CODES = [
    (220191, 2201919),
    (220198, 2201988),
    (220225, 2202251),
    (261153, 2611533),
    (311783, 3117836),
    (315213, 3152131),
    (430587, 4305871),
    (520393, 5203939),
    (520396, 5203962),
]


@pytest.mark.parametrize("six_digits,official", OFFICIAL_CODES)
def test_exceptional_add_dv(six_digits, official):
    assert add_dv(six_digits).item() == official


def test_ordinary_add_dv_and_compatibility():
    assert add_dv(330455).item() == 3304557
    assert add_dv(2201911).item() == 2201911
    assert add_dv("invalid").item() is None
    with pytest.raises(TypeError):
        EXCEPTIONAL_GEOCODE_CORRECTIONS[2201911] = 0


@pytest.fixture()
def repair_tables():
    connection = connections["dados"]
    with connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA IF NOT EXISTS "Municipio"')
        cursor.execute('CREATE SCHEMA IF NOT EXISTS "Dengue_global"')
        cursor.execute('DROP TABLE IF EXISTS "Municipio"."Notificacao"')
        cursor.execute('DROP TABLE IF EXISTS "Dengue_global"."parameters"')
        cursor.execute("""
            CREATE TABLE "Municipio"."Notificacao" (
                id BIGSERIAL PRIMARY KEY,
                nu_notific TEXT NOT NULL,
                dt_notific DATE,
                cid10_codigo TEXT NOT NULL,
                municipio_geocodigo INTEGER NOT NULL,
                cs_sexo TEXT,
                extra_payload INTEGER,
                "quoted payload" TEXT,
                CONSTRAINT casos_unicos UNIQUE (
                    nu_notific, dt_notific, cid10_codigo, municipio_geocodigo
                )
            )
        """)
        cursor.execute("""
            CREATE TABLE "Dengue_global"."parameters" (
                municipio_geocodigo INTEGER NOT NULL,
                cid10 TEXT NOT NULL,
                value INTEGER,
                UNIQUE (municipio_geocodigo, cid10)
            )
        """)
    yield connection
    with connection.cursor() as cursor:
        cursor.execute('DROP TABLE "Municipio"."Notificacao"')
        cursor.execute('DROP TABLE "Dengue_global"."parameters"')


def insert_notification(
    connection,
    code,
    sex=None,
    extra=None,
    quoted=None,
    number="123",
    date="2011-01-01",
    cid="A90",
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO "Municipio"."Notificacao" (
                nu_notific, dt_notific, cid10_codigo, municipio_geocodigo,
                cs_sexo, extra_payload, "quoted payload"
            ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
            [number, date, cid, code, sex, extra, quoted],
        )
        return cursor.fetchone()[0]


def table_rows(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table} ORDER BY 1, 2")
        return cursor.fetchall()


def notifications(connection):
    return table_rows(connection, '"Municipio"."Notificacao"')


def parameters(connection):
    return table_rows(connection, '"Dengue_global"."parameters"')


def run_repair(apply=False):
    output = StringIO()
    call_command("fix_notification_geocodes", apply=apply, stdout=output)
    return output.getvalue()


@pytest.mark.django_db(transaction=True, databases=["default", "dados"])
class TestRepair:
    def test_apply_lock_timeout_is_local(self, repair_tables):
        db = repair_tables
        timeouts = []
        with db.cursor() as cursor:
            cursor.execute("SHOW lock_timeout")
            original_timeout = cursor.fetchone()[0]

        def check_timeout(execute, sql, params, many, context):
            if sql.startswith("LOCK TABLE"):
                with db.cursor() as cursor:
                    cursor.execute("SHOW lock_timeout")
                    timeouts.append(cursor.fetchone()[0])
            return execute(sql, params, many, context)

        with db.execute_wrapper(check_timeout):
            run_repair(apply=True)
        assert timeouts == ["10s"]
        with db.cursor() as cursor:
            cursor.execute("SHOW lock_timeout")
            assert cursor.fetchone()[0] == original_timeout

    def test_busy_ingestion_lock_aborts_without_changes(self, repair_tables):
        db = repair_tables
        insert_notification(db, 2202257)
        before = notifications(db)
        writer = db.Database.connect(**db.get_connection_params())
        try:
            with writer.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO "Municipio"."Notificacao" (
                        nu_notific, cid10_codigo, municipio_geocodigo
                    ) VALUES ('writing', 'A90', 3304557)
                """)
            with pytest.raises(OperationalError, match="lock timeout"):
                run_repair(apply=True)
            assert notifications(db) == before
        finally:
            writer.rollback()
            writer.close()

    def test_final_duplicate_check_excludes_unrelated_geocodes(
        self, repair_tables
    ):
        db = repair_tables
        with db.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE "Municipio"."Notificacao"
                DROP CONSTRAINT casos_unicos
            """)
        insert_notification(db, 3304557)
        insert_notification(db, 3304557)
        insert_notification(db, 2202257)
        run_repair(apply=True)
        rows = notifications(db)
        assert [row[4] for row in rows] == [3304557, 3304557, 2202251]

    def test_dry_run_is_read_only(self, repair_tables):
        db = repair_tables
        insert_notification(db, 2201911, "F", 42)
        insert_notification(db, 2201919, "M")
        before = notifications(db)
        statements = []

        def capture(execute, sql, params, many, context):
            statements.append(sql)
            return execute(sql, params, many, context)

        # PostgreSQL itself rejects writes, including hidden writes in CTEs.
        with transaction.atomic(using="dados"):
            with db.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            with db.execute_wrapper(capture):
                output = run_repair()
        assert notifications(db) == before
        assert parameters(db) == []
        assert all(
            sql.lstrip().startswith(("SELECT", "WITH", "SAVEPOINT", "RELEASE"))
            for sql in statements
        )
        assert "2201911 2201919 1 1 1 0 1" in output
        assert "DRY-RUN" in output
        assert "AFTER" not in output

    @pytest.mark.parametrize(
        "wrong,correct", EXCEPTIONAL_GEOCODE_CORRECTIONS.items()
    )
    def test_wrong_only_and_after_snapshot(
        self, repair_tables, wrong, correct
    ):
        db = repair_tables
        row_id = insert_notification(db, wrong, "F", 42, "retained")
        output = run_repair(apply=True)
        assert notifications(db) == [
            (
                row_id,
                "123",
                date(2011, 1, 1),
                "A90",
                correct,
                "F",
                42,
                "retained",
            )
        ]
        after = output.split("AFTER\n")[1]
        assert f"{wrong} {correct} 0 1 0 0 0" in after
        assert len(after.splitlines()[1:10]) == 9
        for line in after.splitlines()[1:10]:
            assert line.split()[2] == "0"
        before_second = notifications(db)
        run_repair(apply=True)
        assert notifications(db) == before_second

    def test_duplicate_merge_and_unique_constraint(self, repair_tables):
        db = repair_tables
        insert_notification(db, 2201911, "F", 42, "filled")
        canonical_id = insert_notification(db, 2201919, "M", None, None)
        output = run_repair(apply=True)
        rows = notifications(db)
        assert len(rows) == 1
        assert rows[0][0] == canonical_id
        assert rows[0][4:] == (2201919, "M", 42, "filled")
        assert "2201911 2201919 1 1 1 0 1" in output
        with pytest.raises(IntegrityError), transaction.atomic(using="dados"):
            insert_notification(db, 2201919)
        run_repair(apply=True)
        assert notifications(db) == rows

    def test_distinct_natural_keys_and_unrelated_rows(self, repair_tables):
        db = repair_tables
        insert_notification(db, 2202257)
        insert_notification(db, 2202251, number="456")
        insert_notification(db, 2202251, cid="A928")
        insert_notification(db, 2202251, date="2017-01-01")
        unrelated = insert_notification(db, 3304557, "F")
        run_repair(apply=True)
        rows = notifications(db)
        assert len(rows) == 5
        assert sum(row[4] == 2202251 for row in rows) == 4
        assert next(row for row in rows if row[0] == unrelated)[4:] == (
            3304557,
            "F",
            None,
            None,
        )

    def test_null_natural_key_matches(self, repair_tables):
        db = repair_tables
        insert_notification(db, 2201911, "F", date=None)
        canonical_id = insert_notification(db, 2201919, date=None)
        run_repair(apply=True)
        rows = notifications(db)
        assert len(rows) == 1
        assert rows[0][0] == canonical_id
        assert rows[0][2] is None
        assert rows[0][5] == "F"

    def test_ambiguous_null_keys_abort(self, repair_tables):
        db = repair_tables
        insert_notification(db, 2201911, "F", date=None)
        insert_notification(db, 2201911, "M", date=None)
        before = notifications(db)
        with pytest.raises(CommandError, match="Ambiguous"):
            run_repair(apply=True)
        assert notifications(db) == before

    def test_parameter_repair(self, repair_tables):
        db = repair_tables
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO "Dengue_global"."parameters" VALUES
                (2201911, 'A90', 1), (2201919, 'A90', 2),
                (3304557, 'A90', 3)
            """)
        before = parameters(db)
        run_repair()
        assert parameters(db) == before
        run_repair(apply=True)
        assert parameters(db) == [(2201919, "A90", 2), (3304557, "A90", 3)]
        run_repair(apply=True)
        assert parameters(db) == [(2201919, "A90", 2), (3304557, "A90", 3)]

    @pytest.mark.parametrize("apply", [False, True])
    def test_orphan_parameter_aborts(self, repair_tables, apply):
        db = repair_tables
        insert_notification(db, 2202257)
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO "Dengue_global"."parameters" VALUES
                (2201911, 'A90', 1), (2201919, 'A928', 2)
            """)
        before = notifications(db), parameters(db)
        with pytest.raises(CommandError, match="no corrected counterpart"):
            run_repair(apply=apply)
        assert (notifications(db), parameters(db)) == before

    def test_failed_postcondition_rolls_back(self, repair_tables, monkeypatch):
        db = repair_tables
        insert_notification(db, 2202257)
        insert_notification(db, 2201911, "F", 42)
        insert_notification(db, 2201919, "M")
        before = notifications(db)
        original = Command.snapshot

        def broken_after(command, cursor, conflict):
            rows = original(command, cursor, conflict)
            if not any(row[2] for row in rows):
                rows[0] = (*rows[0][:3], 999, *rows[0][4:])
            return rows

        monkeypatch.setattr(Command, "snapshot", broken_after)
        with pytest.raises(CommandError, match="counts failed"):
            run_repair(apply=True)
        assert notifications(db) == before
