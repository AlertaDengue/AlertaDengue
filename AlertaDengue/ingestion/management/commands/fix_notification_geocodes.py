from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, router, transaction
from django.db.backends.utils import CursorWrapper

from dados.models.municipio import Notification
from ingestion.utils import EXCEPTIONAL_GEOCODE_CORRECTIONS

NOTIFICATIONS = '"Municipio"."Notificacao"'
PARAMETERS = '"Dengue_global"."parameters"'
KEY_COLUMNS = (
    "nu_notific",
    "dt_notific",
    "cid10_codigo",
    "municipio_geocodigo",
)
COUNTERPART = (
    " AND ".join(
        f"c.{column} IS NOT DISTINCT FROM w.{column}"
        for column in KEY_COLUMNS[:3]
    )
    + " AND c.municipio_geocodigo = m.correct"
)
MAPPINGS = sorted(EXCEPTIONAL_GEOCODE_CORRECTIONS.items())
MAPPING_SQL = (
    "WITH corrections(invalid, correct) AS (VALUES "
    + ", ".join(["(%s, %s)"] * len(MAPPINGS))
    + ") "
)
MAPPING_PARAMS = tuple(value for pair in MAPPINGS for value in pair)


class Command(BaseCommand):
    help = "Repair the nine known historical notification geocodes (dry-run)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true", help="Apply the repair atomically."
        )

    def handle(self, *args, **options):
        alias = router.db_for_write(Notification)
        connection = connections[alias]
        with transaction.atomic(using=alias), connection.cursor() as cursor:
            if options["apply"]:
                cursor.execute("SET LOCAL lock_timeout = '10s'")
                # Block ingestion and parameter writes until validation commits.
                cursor.execute(
                    f"LOCK TABLE {NOTIFICATIONS}, {PARAMETERS} "
                    "IN SHARE ROW EXCLUSIVE MODE"
                )
            cursor.execute(
                "SELECT attname FROM pg_attribute "
                "WHERE attrelid = %s::regclass AND attnum > 0 "
                "AND NOT attisdropped AND attgenerated = '' "
                "AND attidentity = '' ORDER BY attnum",
                [NOTIFICATIONS],
            )
            payload = [
                connection.ops.quote_name(row[0])
                for row in cursor.fetchall()
                if row[0] not in {"id", *KEY_COLUMNS}
            ]
            conflict = (
                " OR ".join(
                    f"(c.{column} IS NOT NULL AND w.{column} IS NOT NULL "
                    f"AND to_jsonb(c.{column}) IS DISTINCT FROM "
                    f"to_jsonb(w.{column}))"
                    for column in payload
                )
                or "FALSE"
            )
            before = self.snapshot(cursor, conflict)
            self.print_snapshot("BEFORE", before)
            self.check_parameters(cursor)
            if not options["apply"]:
                self.stdout.write("DRY-RUN: no data changed. Use --apply.")
                return

            # NULL key values are compared safely. Ambiguous logical copies
            # cannot be merged deterministically, even if UNIQUE allows them.
            cursor.execute(
                MAPPING_SQL + f"SELECT 1 FROM {NOTIFICATIONS} n "
                "WHERE municipio_geocodigo IN "
                "(SELECT invalid FROM corrections UNION ALL "
                "SELECT correct FROM corrections) "
                f"GROUP BY {', '.join(KEY_COLUMNS)} "
                "HAVING count(*) > 1 LIMIT 1",
                MAPPING_PARAMS,
            )
            if cursor.fetchone():
                raise CommandError(
                    "Ambiguous notification keys; repair aborted."
                )

            # Retain expected IDs and keys in PostgreSQL, including wrong-only
            # rows and canonical rows. No production rows are loaded in Python.
            cursor.execute(
                "CREATE TEMP TABLE geocode_repair_expected ON COMMIT DROP AS "
                + MAPPING_SQL
                + f"SELECT w.id, w.nu_notific, w.dt_notific, w.cid10_codigo, "
                "m.correct AS municipio_geocodigo "
                f"FROM {NOTIFICATIONS} w JOIN corrections m "
                "ON w.municipio_geocodigo = m.correct "
                "OR (w.municipio_geocodigo = m.invalid AND NOT EXISTS "
                f"(SELECT 1 FROM {NOTIFICATIONS} c WHERE {COUNTERPART}))",
                MAPPING_PARAMS,
            )
            if payload:
                assignments = ", ".join(
                    f"{column} = COALESCE(c.{column}, w.{column})"
                    for column in payload
                )
                fillable = " OR ".join(
                    f"(c.{column} IS NULL AND w.{column} IS NOT NULL)"
                    for column in payload
                )
                cursor.execute(
                    MAPPING_SQL + f"UPDATE {NOTIFICATIONS} c "
                    f"SET {assignments} FROM {NOTIFICATIONS} w, corrections m "
                    "WHERE w.municipio_geocodigo = m.invalid "
                    f"AND {COUNTERPART} AND ({fillable})",
                    MAPPING_PARAMS,
                )
            cursor.execute(
                MAPPING_SQL + f"DELETE FROM {NOTIFICATIONS} w "
                f"USING corrections m, {NOTIFICATIONS} c "
                "WHERE w.municipio_geocodigo = m.invalid "
                f"AND {COUNTERPART}",
                MAPPING_PARAMS,
            )
            cursor.execute(
                MAPPING_SQL + f"UPDATE {NOTIFICATIONS} w "
                "SET municipio_geocodigo = m.correct FROM corrections m "
                "WHERE w.municipio_geocodigo = m.invalid",
                MAPPING_PARAMS,
            )
            cursor.execute(
                MAPPING_SQL + f"DELETE FROM {PARAMETERS} w "
                f"USING corrections m, {PARAMETERS} c "
                "WHERE w.municipio_geocodigo = m.invalid "
                "AND c.municipio_geocodigo = m.correct "
                "AND c.cid10 IS NOT DISTINCT FROM w.cid10",
                MAPPING_PARAMS,
            )
            after = self.snapshot(cursor, conflict)
            self.print_snapshot("AFTER", after)
            self.validate(cursor, before, after)
            cursor.execute("DROP TABLE geocode_repair_expected")
        self.stdout.write("Repair committed.")

    def snapshot(self, cursor: CursorWrapper, conflict: str) -> list[tuple]:
        cursor.execute(
            MAPPING_SQL + "SELECT m.invalid, m.correct, count(w.id), "
            f"(SELECT count(*) FROM {NOTIFICATIONS} n "
            "WHERE n.municipio_geocodigo = m.correct), count(c.id), "
            "count(w.id) FILTER (WHERE c.id IS NULL), "
            f"count(w.id) FILTER (WHERE c.id IS NOT NULL AND ({conflict})) "
            f"FROM corrections m LEFT JOIN {NOTIFICATIONS} w "
            "ON w.municipio_geocodigo = m.invalid "
            f"LEFT JOIN {NOTIFICATIONS} c ON {COUNTERPART} "
            "GROUP BY m.invalid, m.correct ORDER BY m.invalid",
            MAPPING_PARAMS,
        )
        return cursor.fetchall()

    def print_snapshot(self, label: str, rows: list[tuple]) -> None:
        self.stdout.write(label)
        self.stdout.write(
            "invalid correct invalid_rows correct_rows matched "
            "invalid_only conflicts"
        )
        for row in rows:
            self.stdout.write(" ".join(str(value) for value in row))

    def check_parameters(self, cursor: CursorWrapper) -> None:
        cursor.execute(
            MAPPING_SQL + f"SELECT w.municipio_geocodigo, w.cid10 "
            f"FROM {PARAMETERS} w JOIN corrections m "
            "ON w.municipio_geocodigo = m.invalid WHERE NOT EXISTS "
            f"(SELECT 1 FROM {PARAMETERS} c "
            "WHERE c.municipio_geocodigo = m.correct "
            "AND c.cid10 IS NOT DISTINCT FROM w.cid10) LIMIT 1",
            MAPPING_PARAMS,
        )
        orphan = cursor.fetchone()
        if orphan:
            raise CommandError(
                f"Invalid parameter {orphan} has no corrected counterpart; "
                "repair aborted."
            )

    def validate(
        self, cursor: CursorWrapper, before: list[tuple], after: list[tuple]
    ) -> None:
        if any(
            new[2] or new[4] or new[5] or new[3] != old[3] + old[5]
            for old, new in zip(before, after)
        ):
            raise CommandError("Notification counts failed validation.")
        cursor.execute(
            "SELECT id, "
            + ", ".join(KEY_COLUMNS)
            + " FROM geocode_repair_expected EXCEPT SELECT id, "
            + ", ".join(KEY_COLUMNS)
            + f" FROM {NOTIFICATIONS} LIMIT 1"
        )
        if cursor.fetchone():
            raise CommandError("Expected notification IDs/keys were lost.")
        cursor.execute(
            MAPPING_SQL
            + f"SELECT 1 FROM {NOTIFICATIONS} "
            + "WHERE municipio_geocodigo IN "
            "(SELECT correct FROM corrections) AND "
            + " AND ".join(f"{column} IS NOT NULL" for column in KEY_COLUMNS)
            + f" GROUP BY {', '.join(KEY_COLUMNS)} "
            "HAVING count(*) > 1 LIMIT 1",
            MAPPING_PARAMS,
        )
        if cursor.fetchone():
            raise CommandError("casos_unicos duplicates remain.")
        cursor.execute(
            MAPPING_SQL + f"SELECT 1 FROM {PARAMETERS} w "
            "JOIN corrections m ON w.municipio_geocodigo = m.invalid LIMIT 1",
            MAPPING_PARAMS,
        )
        if cursor.fetchone():
            raise CommandError("Invalid parameters remain.")
