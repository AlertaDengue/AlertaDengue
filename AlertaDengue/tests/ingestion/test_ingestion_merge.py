from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.utils import timezone
from ingestion.models import Run, RunStatus, SourceFormat
from ingestion.tasks import (
    SINAN_DEST_COLUMNS,
    sinan_merge_run,
    sinan_stage_run,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine

_SINAN_TEST_COLUMNS: list[str] = [
    "ID_MUNICIP",
    "ID_AGRAVO",
    "DT_NOTIFIC",
    "SEM_NOT",
    "NU_ANO",
    "NU_NOTIFIC",
    "DT_SIN_PRI",
    "SEM_PRI",
    "DT_DIGITA",
    "DT_NASC",
    "NU_IDADE_N",
    "CS_SEXO",
    "DT_CHIK_S1",
    "DT_CHIK_S2",
    "DT_PRNT",
    "DT_SORO",
    "DT_NS1",
    "DT_VIRAL",
    "DT_PCR",
]


@pytest.fixture()
def db_engine() -> Engine:
    """
    Return the SQLAlchemy engine configured by Django settings.
    """
    return getattr(settings, "DB_ENGINE")


@pytest.fixture()
def municipio_notificacao_table(db_engine: Engine) -> None:
    """
    Create a minimal Municipio.Notificacao table with casos_unicos constraint.
    """
    key_types: dict[str, str] = {
        "nu_notific": "INTEGER",
        "dt_notific": "DATE",
        "cid10_codigo": "TEXT",
        "municipio_geocodigo": "INTEGER",
    }

    cols_sql = ",\n".join(
        f'"{col}" {key_types.get(col, "TEXT")}' for col in SINAN_DEST_COLUMNS
    )

    create_sql = f"""
        CREATE SCHEMA IF NOT EXISTS "Municipio";
        DROP TABLE IF EXISTS "Municipio"."Notificacao" CASCADE;
        CREATE TABLE "Municipio"."Notificacao" (
            {cols_sql},
            CONSTRAINT casos_unicos UNIQUE (
                nu_notific, dt_notific, cid10_codigo, municipio_geocodigo
            )
        );
    """

    with db_engine.begin() as conn:
        conn.execute(text(create_sql))


def _sha256_file(path: Path) -> str:
    """
    Compute SHA-256 hex digest for a file.

    Parameters
    ----------
    path
        File path.

    Returns
    -------
    str
        SHA-256 hex digest.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Fill required SINAN columns so parsing does not introduce NaN floats.

    Parameters
    ----------
    row
        Input row.

    Returns
    -------
    dict[str, Any]
        Normalized row.
    """
    out = dict(row)

    out.setdefault("ID_AGRAVO", "A90")
    out.setdefault("CS_SEXO", "M")
    out.setdefault("NU_IDADE_N", 0)

    out.setdefault("DT_NOTIFIC", "2025-01-01")
    out.setdefault("DT_SIN_PRI", out["DT_NOTIFIC"])
    out.setdefault("DT_DIGITA", out["DT_NOTIFIC"])
    out.setdefault("DT_NASC", "1990-01-01")

    out.setdefault("DT_CHIK_S1", out["DT_NOTIFIC"])
    out.setdefault("DT_CHIK_S2", out["DT_NOTIFIC"])
    out.setdefault("DT_PRNT", out["DT_NOTIFIC"])
    out.setdefault("DT_SORO", out["DT_NOTIFIC"])
    out.setdefault("DT_NS1", out["DT_NOTIFIC"])
    out.setdefault("DT_VIRAL", out["DT_NOTIFIC"])
    out.setdefault("DT_PCR", out["DT_NOTIFIC"])

    if "SEM_NOT" in out:
        out.setdefault("SEM_PRI", out["SEM_NOT"])
        out.setdefault("NU_ANO", int(str(out["SEM_NOT"])[:4]))

    return out


def _write_sinan_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """
    Write a small SINAN-like CSV (semicolon-separated).

    Parameters
    ----------
    path
        Output path.
    rows
        Rows to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    norm_rows = [_normalize_row(r) for r in rows]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=_SINAN_TEST_COLUMNS,
            delimiter=";",
            extrasaction="ignore",
        )
        writer.writeheader()
        for r in norm_rows:
            writer.writerow(r)


def _create_run(csv_path: Path, *, year: int, week: int) -> Run:
    """
    Create an ingestion.run row pointing to a local CSV.

    Parameters
    ----------
    csv_path
        Source CSV path.
    year
        Delivery year.
    week
        Delivery week.

    Returns
    -------
    Run
        Created run.
    """
    stat = csv_path.stat()
    return Run.objects.create(
        status=RunStatus.QUEUED,
        uf="BR",
        source_format=SourceFormat.CSV,
        disease="A90",
        delivery_year=year,
        delivery_week=week,
        source_path=str(csv_path),
        filename=csv_path.name,
        sha256=_sha256_file(csv_path),
        size_bytes=stat.st_size,
        mtime=timezone.now(),
        metadata={},
        errors=[],
    )


def _get_meta_int(meta: dict[str, Any], key: str) -> int:
    """
    Read an integer-like value from metadata.

    Parameters
    ----------
    meta
        Metadata dict.
    key
        Metadata key.

    Returns
    -------
    int
        Parsed integer (defaults to 0 when missing/blank).
    """
    raw = meta.get(key, 0)
    if raw in (None, ""):
        return 0
    return int(raw)


@pytest.mark.django_db(transaction=True)
def test_stage_and_merge_persists_metrics_no_duplicates(
    tmp_path: Path,
    db_engine: Engine,
    municipio_notificacao_table: None,
) -> None:
    """
    Stage + merge a delivery without duplicate casos_unicos keys.
    """
    csv_path = tmp_path / "den.csv"
    _write_sinan_csv(
        csv_path,
        [
            {
                "ID_MUNICIP": 3304557,
                "NU_NOTIFIC": 1001,
                "DT_NOTIFIC": "2025-01-10",
                "SEM_NOT": 202501,
                "CS_SEXO": "M",
            },
            {
                "ID_MUNICIP": 3303302,
                "NU_NOTIFIC": 1002,
                "DT_NOTIFIC": "2025-01-12",
                "SEM_NOT": 202502,
                "CS_SEXO": "F",
            },
        ],
    )
    run = _create_run(csv_path, year=2026, week=9)

    sinan_stage_run.run(str(run.id))
    res = sinan_merge_run.run(str(run.id))

    run.refresh_from_db()
    meta = dict(run.metadata or {})

    assert run.status == RunStatus.COMPLETED
    assert res["inserted"] == 2
    assert res["updated"] == 0

    assert _get_meta_int(meta, "duplicates_removed") == 0
    assert _get_meta_int(meta, "rows_inserted") == 2
    assert _get_meta_int(meta, "rows_updated") == 0
    assert int(run.rows_loaded) == 2

    if hasattr(run, "rows_duplicate"):
        assert int(getattr(run, "rows_duplicate")) == 0

    with db_engine.begin() as conn:
        count = conn.execute(
            text('SELECT COUNT(*) FROM "Municipio"."Notificacao"')
        ).scalar_one()
    assert int(count) == 2


@pytest.mark.django_db(transaction=True)
def test_merge_deduplicates_stage_and_updates_existing_row(
    tmp_path: Path,
    db_engine: Engine,
    municipio_notificacao_table: None,
) -> None:
    """
    Duplicate casos_unicos keys must be deduped before UPSERT.
    """
    csv_path = tmp_path / "den_dupes.csv"
    _write_sinan_csv(
        csv_path,
        [
            {
                "ID_MUNICIP": 3205309,
                "NU_NOTIFIC": 6381611,
                "DT_NOTIFIC": "2025-01-10",
                "SEM_NOT": 202501,
                "CS_SEXO": "M",
            },
            {
                "ID_MUNICIP": 3205309,
                "NU_NOTIFIC": 6381611,
                "DT_NOTIFIC": "2025-01-10",
                "SEM_NOT": 202501,
                "CS_SEXO": "M",
            },
            {
                "ID_MUNICIP": 3205002,
                "NU_NOTIFIC": 6417939,
                "DT_NOTIFIC": "2025-02-03",
                "SEM_NOT": 202505,
                "CS_SEXO": "F",
            },
        ],
    )
    run = _create_run(csv_path, year=2026, week=9)

    with db_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO "Municipio"."Notificacao" (
                    nu_notific, dt_notific, cid10_codigo, municipio_geocodigo,
                    cs_sexo
                ) VALUES (
                    :nu_notific, :dt_notific, :cid10_codigo, :geo, :cs_sexo
                )
                """
            ),
            {
                "nu_notific": 6417939,
                "dt_notific": "2025-02-03",
                "cid10_codigo": "A90",
                "geo": 3205002,
                "cs_sexo": "M",
            },
        )

    sinan_stage_run.run(str(run.id))
    res = sinan_merge_run.run(str(run.id))

    run.refresh_from_db()
    meta = dict(run.metadata or {})

    assert run.status == RunStatus.COMPLETED
    assert res["inserted"] == 1
    assert res["updated"] == 1

    assert _get_meta_int(meta, "duplicates_removed") == 1
    assert _get_meta_int(meta, "rows_inserted") == 1
    assert _get_meta_int(meta, "rows_updated") == 1

    if hasattr(run, "rows_duplicate"):
        assert int(getattr(run, "rows_duplicate")) == 1

    with db_engine.begin() as conn:
        sexo = conn.execute(
            text(
                """
                SELECT cs_sexo
                FROM "Municipio"."Notificacao"
                WHERE nu_notific = :nu
                  AND dt_notific = :dt
                  AND cid10_codigo = :cid
                  AND municipio_geocodigo = :geo
                """
            ),
            {
                "nu": 6417939,
                "dt": "2025-02-03",
                "cid": "A90",
                "geo": 3205002,
            },
        ).scalar_one()
    assert sexo == "F"
