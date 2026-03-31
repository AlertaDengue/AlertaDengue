from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

CUTOFF = pd.Timestamp("2023-06-01")
STAGE_TABLE = "public.chik_fill_stage"
KEY_COLUMNS = ["data_iniSE", "municipio_geocodigo", "SE"]


@dataclass(frozen=True)
class Diagnostics:
    """Diagnostics for the chikungunya casprov backfill."""

    stage_rows: int
    matched_rows: int
    parquet_rows_without_target: int
    target_rows_without_parquet: int
    target_null_before_cutoff: int


def build_stage_dataframe(parquet_path: Path) -> pd.DataFrame:
    """Build the staging dataframe from the source parquet."""
    if not parquet_path.exists():
        raise CommandError(f"Parquet file not found: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    required_columns = {"date", "geocode", "casprov", "epiweek"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise CommandError(
            f"Missing required parquet columns: {sorted(missing_columns)}"
        )

    df = df.loc[
        df["date"] < CUTOFF,
        ["date", "geocode", "casprov", "epiweek"],
    ].copy()

    df = df.rename(
        columns={
            "date": "data_iniSE",
            "geocode": "municipio_geocodigo",
            "epiweek": "SE",
        }
    )

    df["data_iniSE"] = pd.to_datetime(df["data_iniSE"]).dt.date
    df["municipio_geocodigo"] = pd.to_numeric(
        df["municipio_geocodigo"],
        errors="raise",
    ).astype("int64")
    df["casprov"] = pd.to_numeric(
        df["casprov"],
        errors="raise",
    ).astype("int64")
    df["SE"] = pd.to_numeric(
        df["SE"],
        errors="raise",
    ).astype("int64")

    duplicated_keys = int(df.duplicated(subset=KEY_COLUMNS).sum())
    if duplicated_keys:
        raise CommandError(f"Found {duplicated_keys} duplicated source keys.")

    return df[["data_iniSE", "municipio_geocodigo", "casprov", "SE"]]


def execute_sql(sql: str) -> None:
    """Execute a SQL statement without returning rows."""
    with connection.cursor() as cursor:
        cursor.execute(sql)


def fetch_int(sql: str) -> int:
    """Execute a SQL query that returns a single integer value."""
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()

    if row is None:
        raise CommandError("Query returned no rows.")

    return int(row[0])


def recreate_stage_table() -> None:
    """Drop and recreate the staging table."""
    execute_sql(
        f"""
        DROP TABLE IF EXISTS {STAGE_TABLE};

        CREATE TABLE {STAGE_TABLE} (
            "data_iniSE" date NOT NULL,
            municipio_geocodigo integer NOT NULL,
            casprov integer NOT NULL,
            "SE" integer NOT NULL,
            PRIMARY KEY ("data_iniSE", municipio_geocodigo, "SE")
        );
        """
    )


def copy_stage_dataframe(df: pd.DataFrame) -> None:
    """Bulk load the staging dataframe into PostgreSQL."""
    with NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        encoding="utf-8",
        newline="",
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
        df.to_csv(tmp, index=False)

    try:
        connection.ensure_connection()
        raw_connection = connection.connection
        if raw_connection is None:
            raise CommandError("Raw database connection is unavailable.")

        with raw_connection.cursor() as cursor:
            with tmp_path.open("r", encoding="utf-8", newline="") as handle:
                cursor.copy_expert(
                    f"""
                    COPY {STAGE_TABLE} (
                        "data_iniSE",
                        municipio_geocodigo,
                        casprov,
                        "SE"
                    )
                    FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
                    """,
                    handle,
                )
    finally:
        tmp_path.unlink(missing_ok=True)


def collect_diagnostics() -> Diagnostics:
    """Collect diagnostics for staging and target comparison."""
    stage_rows = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM {STAGE_TABLE};
        """
    )

    matched_rows = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM {STAGE_TABLE} AS s
        JOIN "Municipio"."Historico_alerta_chik" AS t
          ON t."data_iniSE" = s."data_iniSE"
         AND t.municipio_geocodigo = s.municipio_geocodigo
         AND t."SE" = s."SE"
        WHERE t."data_iniSE" < DATE '2023-06-01';
        """
    )

    parquet_rows_without_target = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM {STAGE_TABLE} AS s
        LEFT JOIN "Municipio"."Historico_alerta_chik" AS t
          ON t."data_iniSE" = s."data_iniSE"
         AND t.municipio_geocodigo = s.municipio_geocodigo
         AND t."SE" = s."SE"
        WHERE t.id IS NULL;
        """
    )

    target_rows_without_parquet = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM "Municipio"."Historico_alerta_chik" AS t
        LEFT JOIN {STAGE_TABLE} AS s
          ON t."data_iniSE" = s."data_iniSE"
         AND t.municipio_geocodigo = s.municipio_geocodigo
         AND t."SE" = s."SE"
        WHERE t."data_iniSE" < DATE '2023-06-01'
          AND s."data_iniSE" IS NULL;
        """
    )

    target_null_before_cutoff = fetch_int(
        """
        SELECT COUNT(*)
        FROM "Municipio"."Historico_alerta_chik"
        WHERE "data_iniSE" < DATE '2023-06-01'
          AND casprov IS NULL;
        """
    )

    return Diagnostics(
        stage_rows=stage_rows,
        matched_rows=matched_rows,
        parquet_rows_without_target=parquet_rows_without_target,
        target_rows_without_parquet=target_rows_without_parquet,
        target_null_before_cutoff=target_null_before_cutoff,
    )


def apply_backfill() -> int:
    """Apply the casprov backfill for matched rows only."""
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE "Municipio"."Historico_alerta_chik" AS t
            SET casprov = s.casprov
            FROM {STAGE_TABLE} AS s
            WHERE t."data_iniSE" = s."data_iniSE"
              AND t.municipio_geocodigo = s.municipio_geocodigo
              AND t."SE" = s."SE"
              AND t."data_iniSE" < DATE '2023-06-01'
              AND t.casprov IS DISTINCT FROM s.casprov;
            """
        )
        return int(cursor.rowcount)


class Command(BaseCommand):
    help = "Load chik parquet into stage and backfill casprov."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--parquet-path",
            required=True,
            type=Path,
        )
        parser.add_argument(
            "--apply",
            action="store_true",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Run the one-time chikungunya casprov backfill."""
        parquet_path = cast(Path, options["parquet_path"])
        apply = bool(options["apply"])

        df = build_stage_dataframe(parquet_path)

        with transaction.atomic():
            recreate_stage_table()
            copy_stage_dataframe(df)

            diagnostics = collect_diagnostics()
            self.stdout.write(f"stage_rows={diagnostics.stage_rows}")
            self.stdout.write(f"matched_rows={diagnostics.matched_rows}")
            self.stdout.write(
                "parquet_rows_without_target="
                f"{diagnostics.parquet_rows_without_target}"
            )
            self.stdout.write(
                "target_rows_without_parquet="
                f"{diagnostics.target_rows_without_parquet}"
            )
            self.stdout.write(
                "target_null_before_cutoff="
                f"{diagnostics.target_null_before_cutoff}"
            )

            if not apply:
                self.stdout.write(
                    "Dry run complete. Re-run with --apply to update."
                )
                return

            updated_rows = apply_backfill()
            remaining_nulls = fetch_int(
                """
                SELECT COUNT(*)
                FROM "Municipio"."Historico_alerta_chik"
                WHERE "data_iniSE" < DATE '2023-06-01'
                  AND casprov IS NULL;
                """
            )

            self.stdout.write(f"updated_rows={updated_rows}")
            self.stdout.write(f"remaining_nulls={remaining_nulls}")
