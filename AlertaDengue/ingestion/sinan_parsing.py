from __future__ import annotations

import datetime as dt
from typing import cast

import pandas as pd
from upload.sinan.utils import (
    derive_epiweek_from_dt_notific,
    infer_date_format,
    parse_data,
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


def _parse_sem_not_year_week(
    sem_not: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """
    Extract ISO year/week from SEM_NOT-like values (e.g. '202602').

    Parameters
    ----------
    sem_not
        SEM_NOT column as strings/objects.

    Returns
    -------
    tuple[pd.Series, pd.Series]
        (year, week) as Int64 series (nullable).
    """
    s = sem_not.astype("string").str.strip()
    year = pd.to_numeric(s.str.slice(0, 4), errors="coerce").astype("Int64")
    week = pd.to_numeric(s.str.slice(4, 6), errors="coerce").astype("Int64")

    return year, week


def _parse_dt_notific_with_sem_not(
    dt_notific: pd.Series,
    sem_not: pd.Series,
) -> pd.Series:
    """
    Parse DT_NOTIFIC choosing between YYYY-MM-DD and YYYY-DD-MM using SEM_NOT.

    Parameters
    ----------
    dt_notific
        Raw DT_NOTIFIC values.
    sem_not
        Raw SEM_NOT values.

    Returns
    -------
    pd.Series
        Parsed dates as dt.date (or None).
    """
    raw = dt_notific.astype("string").str.strip()
    a = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    b = pd.to_datetime(raw, format="%Y-%d-%m", errors="coerce")

    sem_y, sem_w = _parse_sem_not_year_week(sem_not)
    sem_code = (sem_y.astype("Int64") * 100 + sem_w.astype("Int64")).astype(
        "Int64"
    )

    a_iso = a.dt.isocalendar()
    b_iso = b.dt.isocalendar()
    a_code = (
        a_iso.year.astype("Int64") * 100 + a_iso.week.astype("Int64")
    ).astype("Int64")
    b_code = (
        b_iso.year.astype("Int64") * 100 + b_iso.week.astype("Int64")
    ).astype("Int64")

    a_dist = (a_code - sem_code).abs()
    b_dist = (b_code - sem_code).abs()

    has_sem = sem_code.notna()
    choose_b = b.notna() & (a.isna() | (has_sem & (b_dist < a_dist)))

    chosen = a.where(~choose_b, b)
    out = chosen.dt.date
    return out.where(chosen.notna(), None)


def parse_dates_for_run(
    df: pd.DataFrame,
    date_formats: dict[str, str | None],
) -> tuple[pd.DataFrame, dict[str, str | None]]:
    if df.empty:
        return df, date_formats

    updated = dict(date_formats)

    if "DT_NOTIFIC" in df.columns:
        if "SEM_NOT" in df.columns:
            df["DT_NOTIFIC"] = _parse_dt_notific_with_sem_not(
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
    return df, updated_formats
