from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Final

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
import pandas as pd

KEY_COLUMNS: Final[list[str]] = ["municipio_geocodigo", "SE"]

DISEASE_CONFIG: Final[dict[str, dict[str, str]]] = {
    "dengue": {
        "target_table": '"Municipio"."Historico_alerta"',
        "stage_table": "public.dengue_casprov_fill_stage",
        "label": "dengue",
    },
    "chik": {
        "target_table": '"Municipio"."Historico_alerta_chik"',
        "stage_table": "public.chik_casprov_fill_stage",
        "label": "chikungunya",
    },
}

COLUMN_ALIASES: Final[dict[str, str]] = {
    "date": "data_iniSE",
    "data_iniSE": "data_iniSE",
    "geocode": "municipio_geocodigo",
    "municipio_geocodigo": "municipio_geocodigo",
    "epiweek": "SE",
    "SE": "SE",
    "casprov": "casprov",
}


@dataclass(frozen=True)
class Diagnostics:
    stage_rows: int
    matched_rows: int
    source_rows_without_target: int
    target_rows_without_source: int
    target_null_rows_in_scope: int


def execute_sql(sql: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(sql)


def fetch_int(sql: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
    if not row:
        raise CommandError("Expected a scalar integer result, got no rows.")
    return int(row[0])


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for source_name, target_name in COLUMN_ALIASES.items():
        if source_name in df.columns:
            rename_map[source_name] = target_name

    df = df.rename(columns=rename_map)

    required_columns = {*KEY_COLUMNS, "casprov"}
    missing = required_columns.difference(df.columns)
    if missing:
        raise CommandError(
            f"Missing required source columns after normalization: {sorted(missing)}"
        )

    # data_iniSE is optional but allowed
    columns_to_keep = list(required_columns)
    if "data_iniSE" in df.columns:
        columns_to_keep.append("data_iniSE")

    return df[columns_to_keep].copy()


def load_input_dataframe(input_path: Path, input_format: str) -> pd.DataFrame:
    if not input_path.exists():
        raise CommandError(f"Input file not found: {input_path}")

    if input_format == "csv":
        return pd.read_csv(input_path)
    if input_format == "parquet":
        return pd.read_parquet(input_path)

    raise CommandError(f"Unsupported input format: {input_format}")


def validate_epiweek(value: int | None, option_name: str) -> int | None:
    if value is None:
        return None
    if value < 190001 or value > 299953:
        raise CommandError(f"Invalid value for {option_name}: {value}")
    return value


def build_stage_dataframe(
    *,
    input_path: Path,
    input_format: str,
    cutoff_date: pd.Timestamp,
    since_epiweek: int | None,
    until_epiweek: int | None,
) -> pd.DataFrame:
    df = load_input_dataframe(input_path=input_path, input_format=input_format)
    df = normalize_columns(df)

    df["municipio_geocodigo"] = pd.to_numeric(
        df["municipio_geocodigo"], errors="raise"
    ).astype("int64")
    df["SE"] = pd.to_numeric(df["SE"], errors="raise").astype("int64")
    df["casprov"] = pd.to_numeric(df["casprov"], errors="raise")

    if df["casprov"].isna().any():
        null_count = int(df["casprov"].isna().sum())
        raise CommandError(
            f"Source file contains {null_count} null casprov values."
        )

    if (df["casprov"] % 1 != 0).any():
        raise CommandError("Source file contains non-integer casprov values.")

    df["casprov"] = df["casprov"].astype("int64")

    if "data_iniSE" in df.columns:
        df["data_iniSE"] = pd.to_datetime(
            df["data_iniSE"], errors="raise"
        ).dt.date
        df = df.loc[df["data_iniSE"] < cutoff_date.date()].copy()

    if since_epiweek is not None:
        df = df.loc[df["SE"] >= since_epiweek].copy()

    if until_epiweek is not None:
        df = df.loc[df["SE"] <= until_epiweek].copy()

    duplicated_keys = int(df.duplicated(subset=KEY_COLUMNS).sum())
    if duplicated_keys:
        raise CommandError(f"Found {duplicated_keys} duplicated source keys.")

    cols = ["municipio_geocodigo", "SE", "casprov"]
    return df[cols].copy()


def recreate_stage_table(stage_table: str) -> None:
    execute_sql(f"DROP TABLE IF EXISTS {stage_table};")
    execute_sql(
        f"""
        CREATE TABLE {stage_table} (
            municipio_geocodigo integer NOT NULL,
            "SE" integer NOT NULL,
            casprov integer NOT NULL,
            PRIMARY KEY (municipio_geocodigo, "SE")
        );
        """
    )


def copy_stage_dataframe(df: pd.DataFrame, stage_table: str) -> None:
    with NamedTemporaryFile(mode="w+", suffix=".csv", delete=True) as tmp:
        df.to_csv(tmp.name, index=False)

        raw_connection = getattr(connection, "connection", None)
        if raw_connection is None:
            connection.ensure_connection()
            raw_connection = connection.connection

        if raw_connection is None:
            raise CommandError("Could not access raw database connection.")

        with raw_connection.cursor() as cursor:
            with open(tmp.name, "r", encoding="utf-8") as handle:
                cursor.copy_expert(
                    f"""
                    COPY {stage_table} (municipio_geocodigo, "SE", casprov)
                    FROM STDIN
                    WITH (FORMAT CSV, HEADER TRUE)
                    """,
                    handle,
                )


def collect_diagnostics(
    *,
    stage_table: str,
    target_table: str,
    cutoff_date: str,
    since_epiweek: int | None,
    until_epiweek: int | None,
) -> Diagnostics:
    scope_filters = [f"t.\"data_iniSE\" < DATE '{cutoff_date}'"]
    stage_scope_filters = [f"s.\"data_iniSE\" < DATE '{cutoff_date}'"]

    if since_epiweek is not None:
        scope_filters.append(f't."SE" >= {since_epiweek}')
        stage_scope_filters.append(f's."SE" >= {since_epiweek}')

    if until_epiweek is not None:
        scope_filters.append(f't."SE" <= {until_epiweek}')
        stage_scope_filters.append(f's."SE" <= {until_epiweek}')

    target_scope_sql = " AND ".join(scope_filters)

    stage_rows = fetch_int(f"SELECT COUNT(*) FROM {stage_table};")

    matched_rows = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM {stage_table} s
        INNER JOIN {target_table} t
            ON t.municipio_geocodigo = s.municipio_geocodigo
           AND t."SE" = s."SE"
        WHERE {target_scope_sql};
        """
    )

    source_rows_without_target = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM {stage_table} s
        LEFT JOIN {target_table} t
            ON t.municipio_geocodigo = s.municipio_geocodigo
           AND t."SE" = s."SE"
           AND {target_scope_sql}
        WHERE t.municipio_geocodigo IS NULL;
        """
    )

    target_rows_without_source = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM {target_table} t
        LEFT JOIN {stage_table} s
            ON t.municipio_geocodigo = s.municipio_geocodigo
           AND t."SE" = s."SE"
        WHERE {target_scope_sql}
          AND s.municipio_geocodigo IS NULL;
        """
    )

    target_null_rows_in_scope = fetch_int(
        f"""
        SELECT COUNT(*)
        FROM {target_table} t
        WHERE {target_scope_sql}
          AND t.casprov IS NULL;
        """
    )

    return Diagnostics(
        stage_rows=stage_rows,
        matched_rows=matched_rows,
        source_rows_without_target=source_rows_without_target,
        target_rows_without_source=target_rows_without_source,
        target_null_rows_in_scope=target_null_rows_in_scope,
    )


def apply_backfill(
    *,
    stage_table: str,
    target_table: str,
    cutoff_date: str,
    since_epiweek: int | None,
    until_epiweek: int | None,
) -> int:
    filters = [f"t.\"data_iniSE\" < DATE '{cutoff_date}'"]

    if since_epiweek is not None:
        filters.append(f't."SE" >= {since_epiweek}')

    if until_epiweek is not None:
        filters.append(f't."SE" <= {until_epiweek}')

    filters_sql = " AND ".join(filters)

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {target_table} AS t
            SET casprov = s.casprov
            FROM {stage_table} AS s
            WHERE t.municipio_geocodigo = s.municipio_geocodigo
              AND t."SE" = s."SE"
              AND {filters_sql}
              AND t.casprov IS DISTINCT FROM s.casprov;
            """
        )
        return int(cursor.rowcount)


class Command(BaseCommand):
    help = "Backfill casprov values for dengue or chik using CSV or parquet input."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--disease",
            required=True,
            choices=sorted(DISEASE_CONFIG.keys()),
            help="Disease target table to update.",
        )
        parser.add_argument(
            "--input-path",
            required=True,
            help="Path to the input CSV or parquet file inside the container.",
        )
        parser.add_argument(
            "--input-format",
            required=True,
            choices=["csv", "parquet"],
            help="Input file format.",
        )
        parser.add_argument(
            "--cutoff-date",
            default="2023-06-01",
            help="Only update rows with data_iniSE before this date.",
        )
        parser.add_argument(
            "--since-epiweek",
            type=int,
            default=None,
            help="Optional lower bound for SE, inclusive.",
        )
        parser.add_argument(
            "--until-epiweek",
            type=int,
            default=None,
            help="Optional upper bound for SE, inclusive.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the update. Without this flag, only diagnostics are run.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        disease = str(options["disease"])
        input_path = Path(str(options["input_path"]))
        input_format = str(options["input_format"])
        cutoff_date_str = str(options["cutoff_date"])
        cutoff_date = pd.Timestamp(cutoff_date_str)
        since_epiweek = validate_epiweek(
            options["since_epiweek"], "--since-epiweek"
        )
        until_epiweek = validate_epiweek(
            options["until_epiweek"], "--until-epiweek"
        )
        apply = bool(options["apply"])

        if since_epiweek is not None and until_epiweek is not None:
            if since_epiweek > until_epiweek:
                raise CommandError(
                    "--since-epiweek cannot be greater than --until-epiweek"
                )

        config = DISEASE_CONFIG[disease]
        target_table = config["target_table"]
        stage_table = config["stage_table"]
        label = config["label"]

        df = build_stage_dataframe(
            input_path=input_path,
            input_format=input_format,
            cutoff_date=cutoff_date,
            since_epiweek=since_epiweek,
            until_epiweek=until_epiweek,
        )

        self.stdout.write(self.style.NOTICE(f"Disease: {label}"))
        self.stdout.write(self.style.NOTICE(f"Target table: {target_table}"))
        self.stdout.write(self.style.NOTICE(f"Stage table: {stage_table}"))
        self.stdout.write(self.style.NOTICE(f"Input rows in scope: {len(df)}"))

        with transaction.atomic():
            recreate_stage_table(stage_table=stage_table)
            copy_stage_dataframe(df=df, stage_table=stage_table)

            diagnostics = collect_diagnostics(
                stage_table=stage_table,
                target_table=target_table,
                cutoff_date=cutoff_date_str,
                since_epiweek=since_epiweek,
                until_epiweek=until_epiweek,
            )

            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("Diagnostics"))
            self.stdout.write(f"  stage_rows: {diagnostics.stage_rows}")
            self.stdout.write(f"  matched_rows: {diagnostics.matched_rows}")
            self.stdout.write(
                f"  source_rows_without_target: {diagnostics.source_rows_without_target}"
            )
            self.stdout.write(
                f"  target_rows_without_source: {diagnostics.target_rows_without_source}"
            )
            self.stdout.write(
                f"  target_null_rows_in_scope: {diagnostics.target_null_rows_in_scope}"
            )

            if not apply:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING("Dry run only. No rows were updated.")
                )
                return

            updated_rows = apply_backfill(
                stage_table=stage_table,
                target_table=target_table,
                cutoff_date=cutoff_date_str,
                since_epiweek=since_epiweek,
                until_epiweek=until_epiweek,
            )

            remaining_nulls = fetch_int(
                f"""
                SELECT COUNT(*)
                FROM {target_table} t
                WHERE t."data_iniSE" < DATE '{cutoff_date_str}'
                  {'AND t."SE" >= ' + str(since_epiweek) if since_epiweek is not None else ""}
                  {'AND t."SE" <= ' + str(until_epiweek) if until_epiweek is not None else ""}
                  AND t.casprov IS NULL;
                """
            )

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(f"Updated rows: {updated_rows}")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Remaining nulls in scope: {remaining_nulls}"
                )
            )
