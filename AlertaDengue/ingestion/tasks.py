from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

import numpy as np
import pandas as pd
from celery import chain, shared_task
from django.conf import settings
from django.utils import timezone
from ingestion.models import Run, RunStatus, SourceFormat
from ingestion.schemas import RunError, RunMetadata
from ingestion.services import resolve_source_path
from ingestion.sinan_parsing import parse_chunk_to_sinan
from ingestion.sinan_specs import (
    SINAN_DEST_COLUMNS,
    SINAN_SOURCE_TO_DEST_COLUMNS,
    SINAN_SYNONYMS_FIELDS,
)
from ingestion.sources import iter_csv, iter_dbf, iter_parquet
from psycopg2.extras import execute_values

DB_ENGINE: Any = settings.DB_ENGINE


class DataChunk(Protocol):
    df: pd.DataFrame
    chunk_id: int
    row_start: int


@dataclass(frozen=True)
class MergeCounts:
    inserted: int
    updated: int


def _worker_hostname() -> str:
    return os.environ.get("HOSTNAME", "unknown")


def _now() -> Any:
    return timezone.now()


def _stage_table() -> str:
    return '"ingestion"."sinan_stage"'


def _notificacao_table() -> str:
    return '"Municipio"."Notificacao"'


def _normalize_synonyms(df: pd.DataFrame) -> pd.DataFrame:
    for canonical, synonyms in SINAN_SYNONYMS_FIELDS.items():
        if canonical in df.columns:
            continue
        for syn in synonyms:
            if syn in df.columns:
                df[canonical] = df[syn]
                break
    return df


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all expected SINAN source columns exist in the dataframe.

    Parameters
    ----------
    df
        Chunk dataframe.

    Returns
    -------
    pd.DataFrame
        Dataframe with missing columns added as nulls.
    """
    for src_col in SINAN_SOURCE_TO_DEST_COLUMNS.keys():
        if src_col not in df.columns:
            df[src_col] = None
    return df


def _iter_source(
    source: Path,
    source_format: str,
    chunksize: int,
) -> Iterable[DataChunk]:
    if source_format == SourceFormat.PARQUET:
        return iter_parquet(source, chunksize=chunksize)
    if source_format == SourceFormat.CSV:
        return iter_csv(source, chunksize=chunksize)
    if source_format == SourceFormat.DBF:
        return iter_dbf(source, chunksize=chunksize)
    raise ValueError(f"Unsupported source_format: {source_format}")


def _dump_meta(value: dict[str, Any]) -> dict[str, Any]:
    return RunMetadata.model_validate(value).model_dump(mode="json")


def _dump_err(step: str, exc: Exception) -> dict[str, Any]:
    return RunError(
        step=step,
        code=exc.__class__.__name__,
        message=str(exc),
    ).model_dump(mode="json")


def _adapt_psycopg2_value(value: Any) -> Any:
    """
    Convert pandas/numpy scalars into psycopg2-friendly Python types.

    Parameters
    ----------
    value
        Scalar extracted from a pandas dataframe row.

    Returns
    -------
    Any
        Value compatible with psycopg2 (None, int, float, str, date, datetime).
    """
    if value is None or pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


@shared_task(name="ingestion.enqueue_sinan_run")
def enqueue_sinan_run(run_id: str) -> None:
    """
    Enqueue the SINAN ingestion workflow for a given Run.

    Parameters
    ----------
    run_id
        Run UUID.
    """
    run = Run.objects.get(pk=run_id)

    Run.objects.filter(pk=run_id).update(
        status=RunStatus.QUEUED,
        attempts=run.attempts + 1,
        updated_at=_now(),
    )

    if run.status == RunStatus.STAGED and run.rows_parsed > 0:
        sinan_merge_run.si(run_id).apply_async()
        return

    chain(
        sinan_stage_run.si(run_id),
        sinan_merge_run.si(run_id),
    ).apply_async()


@shared_task(name="ingestion.sinan_stage_run")
def sinan_stage_run(run_id: str) -> None:
    """
    Read/parse a SINAN source file and bulk insert canonical rows into
    ingestion.sinan_stage.

    Parameters
    ----------
    run_id
        Run UUID.
    """
    run = Run.objects.get(pk=run_id)
    now = _now()

    Run.objects.filter(pk=run_id).update(
        status=RunStatus.STAGING,
        started_at=run.started_at or now,
        worker_hostname=_worker_hostname(),
        updated_at=now,
    )

    try:
        source = resolve_source_path(run.source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        meta_in = dict(run.metadata or {})
        date_formats = dict(meta_in.get("date_formats", {}))
        meta_out = _dump_meta(meta_in)
        meta_out["source_columns"] = []

        chunksize = 100_000
        iterator = _iter_source(source, run.source_format, chunksize)

        with DB_ENGINE.begin() as conn:
            cursor = conn.connection.cursor()
            cursor.execute(
                f"DELETE FROM {_stage_table()} WHERE run_id = %s",
                [str(run_id)],
            )

            total_read = 0
            total_parsed = 0

            for chunk in iterator:
                df = chunk.df.copy()
                meta_out["source_columns"] = list(df.columns)

                df = _normalize_synonyms(df)
                df = _ensure_columns(df)

                df, date_formats = parse_chunk_to_sinan(
                    df=df,
                    default_cid=run.disease,
                    year=run.delivery_year,
                    date_formats=date_formats,
                )

                df = df.rename(columns=SINAN_SOURCE_TO_DEST_COLUMNS)

                rownums = pd.Series(range(len(df)), dtype="int64")
                source_rownum = (rownums + chunk.row_start + 1).tolist()

                stage_cols = [
                    "run_id",
                    "chunk_id",
                    "source_rownum",
                    *SINAN_DEST_COLUMNS,
                    "created_at",
                ]

                stage_df = df.reindex(columns=SINAN_DEST_COLUMNS)
                stage_df.insert(0, "source_rownum", source_rownum)
                stage_df.insert(0, "chunk_id", int(chunk.chunk_id))
                stage_df.insert(0, "run_id", str(run_id))
                stage_df["created_at"] = _now()

                rows = [
                    tuple(_adapt_psycopg2_value(v) for v in row)
                    for row in stage_df.itertuples(index=False, name=None)
                ]
                sql = (
                    f"INSERT INTO {_stage_table()} "
                    f"({', '.join(stage_cols)}) VALUES %s"
                )
                execute_values(cursor, sql, rows, page_size=5000)

                total_read += len(df)
                total_parsed += len(df)

                meta_saved = _dump_meta(
                    {**meta_out, "date_formats": date_formats},
                )

                Run.objects.filter(pk=run_id).update(
                    rows_read=total_read,
                    rows_parsed=total_parsed,
                    metadata=meta_saved,
                    updated_at=_now(),
                )

        Run.objects.filter(pk=run_id).update(
            status=RunStatus.STAGED,
            updated_at=_now(),
        )

    except Exception as exc:
        run = Run.objects.get(pk=run_id)
        run.append_error(_dump_err("stage", exc))
        run.status = RunStatus.FAILED
        run.finished_at = _now()
        run.save(
            update_fields=["errors", "status", "finished_at", "updated_at"]
        )
        raise


@shared_task(name="ingestion.sinan_merge_run")
def sinan_merge_run(run_id: str) -> dict[str, int]:
    """
    Merge staged SINAN rows into Municipio.Notificacao via UPSERT.

    Parameters
    ----------
    run_id
        Run UUID.

    Returns
    -------
    dict[str, int]
        Inserted/updated counts.
    """
    Run.objects.filter(pk=run_id).update(
        status=RunStatus.MERGING,
        updated_at=_now(),
    )

    try:
        cols = ", ".join(SINAN_DEST_COLUMNS)
        updates = ", ".join(f"{c}=excluded.{c}" for c in SINAN_DEST_COLUMNS)

        sql = f"""
            WITH upsert AS (
                INSERT INTO {_notificacao_table()} ({cols})
                SELECT {cols}
                FROM {_stage_table()}
                WHERE run_id = %s
                ON CONFLICT ON CONSTRAINT casos_unicos
                DO UPDATE SET {updates}
                RETURNING (xmax = 0) AS inserted
            )
            SELECT
                COUNT(*) FILTER (WHERE inserted) AS inserted,
                COUNT(*) FILTER (WHERE NOT inserted) AS updated
            FROM upsert;
        """

        range_sql = f"""
            SELECT
                MIN(ano_notif * 100 + se_notif) AS se_min,
                MAX(ano_notif * 100 + se_notif) AS se_max
            FROM {_stage_table()}
            WHERE run_id = %s;
        """

        with DB_ENGINE.begin() as conn:
            cursor = conn.connection.cursor()
            cursor.execute(sql, [str(run_id)])
            inserted, updated = cursor.fetchone()

            cursor.execute(range_sql, [str(run_id)])
            se_min, se_max = cursor.fetchone()

        meta_in = dict(Run.objects.get(pk=run_id).metadata or {})
        if se_min is not None and se_max is not None:
            meta_in["se_range"] = {"min": int(se_min), "max": int(se_max)}
        meta_out = _dump_meta(meta_in)

        loaded = int(inserted or 0) + int(updated or 0)

        Run.objects.filter(pk=run_id).update(
            rows_loaded=loaded,
            status=RunStatus.COMPLETED,
            finished_at=_now(),
            metadata=meta_out,
            updated_at=_now(),
        )

        return {"inserted": int(inserted or 0), "updated": int(updated or 0)}

    except Exception as exc:
        run = Run.objects.get(pk=run_id)
        run.append_error(_dump_err("merge", exc))
        run.status = RunStatus.FAILED
        run.finished_at = _now()
        run.save(
            update_fields=["errors", "status", "finished_at", "updated_at"]
        )
        raise
