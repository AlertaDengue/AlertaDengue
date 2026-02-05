from __future__ import annotations

import datetime as dt
from typing import cast

import pandas as pd
from upload.sinan.utils import (
    derive_epiweek_from_dt_notific,
    infer_date_format,
    parse_data,
    parse_dt_notific_with_sem_not,
)

DT_COLS: list[str] = [
    "DT_SIN_PRI",
    "DT_DIGITA",
    "DT_NASC",
    "DT_NOTIFIC",
    "DT_CHIK_S1",
    "DT_CHIK_S2",
    "DT_PRNT",
    "DT_SORO",
    "DT_NS1",
    "DT_VIRAL",
    "DT_PCR",
]


def _to_date_series(col: pd.Series, fmt: str | None) -> pd.Series:
    """
    Convert a pandas Series to Python ``datetime.date`` values (or None).

    Parameters
    ----------
    col
        Input series containing date-like values.
    fmt
        Optional datetime format hint.

    Returns
    -------
    pd.Series
        Series of ``datetime.date`` (or None).
    """

    def to_date(v: object) -> dt.date | None:
        if pd.isna(v):
            return None
        if isinstance(v, dt.datetime):
            return v.date()
        if isinstance(v, dt.date):
            return v

        try:
            ts_any = pd.to_datetime(v, format=fmt, errors="raise")
        except Exception:
            return None

        if pd.isna(ts_any):
            return None

        ts = cast(pd.Timestamp, ts_any)
        py_dt = cast(dt.datetime, ts.to_pydatetime())
        return py_dt.date()

    return col.apply(to_date)


def parse_dates_for_run(
    df: pd.DataFrame,
    date_formats: dict[str, str | None],
) -> tuple[pd.DataFrame, dict[str, str | None]]:
    if df.empty:
        return df, date_formats

    updated = dict(date_formats)

    if "DT_NOTIFIC" in df.columns:
        if "SEM_NOT" in df.columns:
            df["DT_NOTIFIC"] = parse_dt_notific_with_sem_not(
                df["DT_NOTIFIC"],
                df["SEM_NOT"],
            )
        else:
            fmt = updated.get("DT_NOTIFIC")
            if fmt is None and df["DT_NOTIFIC"].dtype == "object":
                fmt = infer_date_format(df["DT_NOTIFIC"].astype(str).tolist())
                updated["DT_NOTIFIC"] = fmt
            df["DT_NOTIFIC"] = _to_date_series(df["DT_NOTIFIC"], fmt)

    for col in DT_COLS:
        if col not in df.columns or col == "DT_NOTIFIC":
            continue
        fmt = updated.get(col)
        if fmt is None and df[col].dtype == "object":
            fmt = infer_date_format(df[col].astype(str).tolist())
            updated[col] = fmt
        df[col] = _to_date_series(df[col], fmt)

    return df, updated


def parse_chunk_to_sinan(
    df: pd.DataFrame,
    default_cid: str,
    year: int,
    date_formats: dict[str, str | None],
) -> tuple[pd.DataFrame, dict[str, str | None]]:
    """
    Apply date parsing + SINAN normalization for a chunk.
    """
    df, updated_formats = parse_dates_for_run(df, date_formats)
    df = parse_data(df, default_cid=default_cid, year=year)
    df = derive_epiweek_from_dt_notific(df)

    return df, updated_formats
