from __future__ import annotations

import csv
import importlib.util
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import chardet
import geopandas as gpd
import pandas as pd
from pyarrow import parquet as pq
from simpledbf import Dbf5

from .sinan_specs import (
    SINAN_REQUIRED_COLS,
    SINAN_SOURCE_TO_DEST_COLUMNS,
    SINAN_SYNONYMS_FIELDS,
)
from .types import Chunk
from .utils import chunk_gen

DBF_ENCODING = "ISO-8859-1"


@dataclass(frozen=True, slots=True)
class _ColumnPlan:
    cols_to_read: list[str]
    rename_map: dict[str, str]


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _select_gpd_engine() -> str:
    return "pyogrio" if _has_module("pyogrio") else "fiona"


def _resolve_required_columns(available: set[str]) -> _ColumnPlan:
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

    optional = [
        c
        for c in SINAN_SOURCE_TO_DEST_COLUMNS.keys()
        if c in available and c not in set(cols)
    ]

    return _ColumnPlan(cols_to_read=cols + optional, rename_map=rename_map)


def _read_dbf_header_columns(path: Path, engine: str) -> set[str]:
    df = gpd.read_file(
        str(path),
        rows=slice(0, 1),
        ignore_geometry=True,
        engine=engine,
        encoding=DBF_ENCODING,
        datetime_as_string=True if engine == "pyogrio" else False,
    )
    return set(df.columns)


def _read_dbf_slice(
    path: Path,
    engine: str,
    cols: list[str],
    row_slice: slice,
) -> pd.DataFrame:
    if engine == "pyogrio":
        return gpd.read_file(
            str(path),
            rows=row_slice,
            ignore_geometry=True,
            engine=engine,
            encoding=DBF_ENCODING,
            columns=cols,
            datetime_as_string=True,
        )

    return gpd.read_file(
        str(path),
        rows=row_slice,
        ignore_geometry=True,
        engine=engine,
        encoding=DBF_ENCODING,
        include_fields=cols,
    )


def iter_parquet(path: Path, chunksize: int) -> Iterator[Chunk]:
    parquet = pq.ParquetFile(str(path))
    available = set(parquet.schema.names)
    plan = _resolve_required_columns(available)

    row_start = 0
    for chunk_id, batch in enumerate(
        parquet.iter_batches(batch_size=chunksize, columns=plan.cols_to_read)
    ):
        df = batch.to_pandas()
        if plan.rename_map:
            df = df.rename(columns=plan.rename_map)
        if df.empty:
            continue
        yield Chunk(chunk_id=chunk_id, row_start=row_start, df=df)
        row_start += len(df)


def _detect_csv_encoding(path: Path) -> str:
    raw = path.open("rb").read(20000)
    enc = (chardet.detect(raw).get("encoding") or "latin1").strip()
    if enc.lower() == "ascii":
        return "latin1"
    return enc


def _sniff_csv_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        return dialect.delimiter
    except Exception:
        return ";"


def _read_csv_header_columns(
    path: Path, encoding: str
) -> tuple[list[str], str]:
    raw = path.open("rb").read(20000)
    text = raw.decode(encoding, errors="replace")
    delim = _sniff_csv_delimiter(text)
    first_line = text.splitlines()[0] if text.splitlines() else ""
    cols = next(csv.reader([first_line], delimiter=delim), [])
    cols = [c.strip() for c in cols if c.strip()]
    return cols, delim


def iter_csv(path: Path, chunksize: int) -> Iterator[Chunk]:
    encoding = _detect_csv_encoding(path)
    header_cols, delim = _read_csv_header_columns(path, encoding=encoding)
    plan = _resolve_required_columns(set(header_cols))

    csv.field_size_limit(10**7)

    row_start = 0
    with path.open("rb") as fb:
        wrapper = io.TextIOWrapper(fb, encoding=encoding, errors="replace")
        reader = pd.read_csv(
            wrapper,
            chunksize=chunksize,
            sep=delim,
            engine="python",
            usecols=plan.cols_to_read,
        )
        for chunk_id, df in enumerate(reader):
            if plan.rename_map:
                df = df.rename(columns=plan.rename_map)
            if df.empty:
                continue
            yield Chunk(chunk_id=chunk_id, row_start=row_start, df=df)
            row_start += len(df)


def iter_dbf(path: Path, chunksize: int) -> Iterator[Chunk]:
    engine = _select_gpd_engine()
    available = _read_dbf_header_columns(path, engine=engine)
    plan = _resolve_required_columns(available)

    dbf = Dbf5(str(path), codec=DBF_ENCODING)
    total = int(dbf.numrec)

    row_start = 0
    for chunk_id, (lb, ub) in enumerate(chunk_gen(chunksize, total)):
        df = _read_dbf_slice(
            path,
            engine=engine,
            cols=plan.cols_to_read,
            row_slice=slice(lb, ub),
        )
        if plan.rename_map:
            df = df.rename(columns=plan.rename_map)

        if df.empty:
            raise RuntimeError(
                "DBF returned empty chunk: "
                f"path={path} chunk={chunk_id} rows=[{lb},{ub}) "
                f"engine={engine}"
            )

        yield Chunk(chunk_id=chunk_id, row_start=row_start, df=df)
        row_start += len(df)
