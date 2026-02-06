from __future__ import annotations

import csv
import importlib
from pathlib import Path
from typing import Iterator

import chardet
import geopandas as gpd
import pandas as pd
from ingestion.sinan_specs import SINAN_SOURCE_TO_DEST_COLUMNS
from pyarrow import parquet as pq
from simpledbf import Dbf5
from upload.sinan.utils import chunk_gen

from .sinan_specs import (
    SINAN_REQUIRED_COLS,
    SINAN_SOURCE_TO_DEST_COLUMNS,
    SINAN_SYNONYMS_FIELDS,
)
from .types import Chunk

DBF_ENCODING = "ISO-8859-1"


def _has_module(name: str) -> bool:

    return importlib.util.find_spec(name) is not None


def _select_gpd_engine() -> str:
    return "pyogrio" if _has_module("pyogrio") else "fiona"


def _read_dbf_header_columns(path: Path, engine: str) -> list[str]:
    df = gpd.read_file(
        str(path),
        rows=slice(0, 1),
        ignore_geometry=True,
        engine=engine,
        encoding="ISO-8859-1",
    )
    return list(df.columns)


def _resolve_required_columns(
    available: set[str],
) -> tuple[list[str], dict[str, str]]:
    cols: list[str] = []
    rename_map: dict[str, str] = {}

    for req in SINAN_REQUIRED_COLS:
        if req in available:
            cols.append(req)
            continue

        syns = SINAN_SYNONYMS_FIELDS.get(req, [])
        chosen = next((s for s in syns if s in available), None)
        if chosen is None:
            raise KeyError(f"Missing required SINAN column: {req}")

        cols.append(chosen)
        rename_map[chosen] = req

    return cols, rename_map


def _resolve_optional_columns(available: set[str]) -> list[str]:
    optional = [
        c
        for c in SINAN_SOURCE_TO_DEST_COLUMNS.keys()
        if c in available and c not in SINAN_REQUIRED_COLS
    ]
    return optional


def _read_dbf_slice(
    path: Path,
    engine: str,
    columns: list[str],
    row_slice: slice,
) -> pd.DataFrame:
    if engine == "pyogrio":
        return gpd.read_file(
            str(path),
            rows=row_slice,
            ignore_geometry=True,
            engine=engine,
            encoding="ISO-8859-1",
            columns=columns,
        )

    return gpd.read_file(
        str(path),
        rows=row_slice,
        ignore_geometry=True,
        engine=engine,
        encoding="ISO-8859-1",
        include_fields=columns,
    )


def iter_parquet(path: Path, chunksize: int) -> Iterator[Chunk]:
    parquet = pq.ParquetFile(str(path))
    cols = list(SINAN_SOURCE_TO_DEST_COLUMNS.keys())

    row_start = 0
    for chunk_id, batch in enumerate(
        parquet.iter_batches(batch_size=chunksize, columns=cols)
    ):
        df = batch.to_pandas()
        yield Chunk(chunk_id=chunk_id, row_start=row_start, df=df)
        row_start += len(df)


def iter_csv(path: Path, chunksize: int) -> Iterator[Chunk]:
    raw = path.open("rb").read(20000)
    encoding = chardet.detect(raw)["encoding"] or "latin1"

    csv.field_size_limit(10**6)

    cols = list(SINAN_SOURCE_TO_DEST_COLUMNS.keys())

    row_start = 0
    for chunk_id, df in enumerate(
        pd.read_csv(
            str(path),
            chunksize=chunksize,
            usecols=lambda c: c in cols,
            engine="python",
            sep=None,
            encoding=encoding,
        )
    ):
        yield Chunk(chunk_id=chunk_id, row_start=row_start, df=df)
        row_start += len(df)


def iter_dbf(
    path: Path,
    chunksize: int,
    cols: list[str] | None = None,
) -> Iterator[Chunk]:
    """
    Stream DBF rows in fixed-size chunks using GeoPandas + pyogrio.
    """
    if importlib.util.find_spec("pyogrio") is None:
        raise RuntimeError(
            "DBF chunk reading requires 'pyogrio'. Install it and retry."
        )

    if cols is None:
        cols = list(SINAN_SOURCE_TO_DEST_COLUMNS.keys())

    row_start = 0
    chunk_id = 0

    while True:
        df = gpd.read_file(
            str(path),
            include_fields=cols,
            rows=slice(row_start, row_start + chunksize),
            ignore_geometry=True,
            encoding=DBF_ENCODING,
            engine="pyogrio",
        )

        if df.empty:
            if row_start == 0:
                raise RuntimeError(f"DBF returned 0 rows: {path}")
            break

        yield Chunk(chunk_id=chunk_id, row_start=row_start, df=df)
        row_start += len(df)
        chunk_id += 1
