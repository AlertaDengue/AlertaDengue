from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

import chardet
import geopandas as gpd
import pandas as pd
import pyarrow.parquet as pq
from ingestion.services import chunk_gen
from ingestion.sinan_specs import SINAN_SOURCE_TO_DEST_COLUMNS
from simpledbf import Dbf5


class Chunk:
    """
    A source chunk.

    Parameters
    ----------
    chunk_id : int
        Sequential chunk id.
    row_start : int
        0-based start index in the source.
    df : pd.DataFrame
        Chunk dataframe in source column names.
    """

    def __init__(
        self, chunk_id: int, row_start: int, df: pd.DataFrame
    ) -> None:
        self.chunk_id = chunk_id
        self.row_start = row_start
        self.df = df


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


def iter_dbf(path: Path, chunksize: int) -> Iterator[Chunk]:
    dbf = Dbf5(str(path), codec="iso-8859-1")
    cols = list(SINAN_SOURCE_TO_DEST_COLUMNS.keys())

    row_start = 0
    for chunk_id, (lb, ub) in enumerate(chunk_gen(chunksize, dbf.numrec)):
        df = gpd.read_file(
            str(path),
            include_fields=cols,
            rows=slice(lb, ub),
            ignore_geometry=True,
        )
        yield Chunk(chunk_id=chunk_id, row_start=row_start, df=df)
        row_start += len(df)
