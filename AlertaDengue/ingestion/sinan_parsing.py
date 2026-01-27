from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Iterable

import pandas as pd
from dateutil.parser import parse
from epiweeks import Week
from pandas.tseries.api import guess_datetime_format
from upload.sinan.utils import parse_data

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


import pandas as pd


def enforce_epiweek_from_dt_notific(df: pd.DataFrame) -> pd.DataFrame:
    """Derive (NU_ANO, SEM_NOT) from DT_NOTIFIC when DT_NOTIFIC is present.

    Parameters
    ----------
    df
        Chunk with SINAN columns. Must include ``DT_NOTIFIC``.
        If ``NU_ANO`` / ``SEM_NOT`` exist, they will be overwritten for rows
        where ``DT_NOTIFIC`` is not null.

    Returns
    -------
    pd.DataFrame
        Updated DataFrame.
    """
    if "DT_NOTIFIC" not in df.columns:
        return df

    dt = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce")
    mask = dt.notna()
    if not mask.any():
        return df

    iso = dt.loc[mask].dt.isocalendar()
    df.loc[mask, "NU_ANO"] = iso["year"].astype("Int64")
    df.loc[mask, "SEM_NOT"] = iso["week"].astype("Int64")
    return df


def is_date_ambiguous(value: str) -> bool:
    """
    Determine if a date string is ambiguous for inferring its format.

    Parameters
    ----------
    value : str
        Date string.

    Returns
    -------
    bool
        True if ambiguous, otherwise False.
    """
    try:
        monthfirst = parse(value, dayfirst=False)
        dayfirst = parse(value, dayfirst=True)

        if monthfirst == dayfirst and dayfirst.day != dayfirst.month:
            return False

        if monthfirst.day <= 12:
            return True

        if dayfirst.day <= 12:
            return True

    except (ValueError, TypeError):
        return False

    return False


def infer_date_format(values: Iterable[str]) -> str | None:
    """
    Infer the most common date format in a collection of strings.

    Parameters
    ----------
    values : Iterable[str]
        Date string values.

    Returns
    -------
    str | None
        Most common inferred format, or None if not inferable.
    """
    dates = [d for d in set(values) if d and not is_date_ambiguous(d)]
    scores = Counter(
        fmt
        for fmt in (guess_datetime_format(d) for d in dates)
        if fmt is not None
    )
    return scores.most_common(1)[0][0] if scores else None


def _to_date_series(col: pd.Series, fmt: str | None) -> pd.Series:
    def to_date(v: object) -> dt.date | None:
        if pd.isna(v):
            return None
        if isinstance(v, dt.date):
            return v
        try:
            return pd.to_datetime(v, format=fmt).date()
        except Exception:
            return None

    return col.apply(to_date)


def parse_dates_for_run(
    df: pd.DataFrame,
    date_formats: dict[str, str | None],
) -> tuple[pd.DataFrame, dict[str, str | None]]:
    """
    Parse DT_* columns to date and infer formats when needed.

    Parameters
    ----------
    df : pd.DataFrame
        Input chunk.
    date_formats : dict[str, str | None]
        Previously known formats, will be updated.

    Returns
    -------
    tuple[pd.DataFrame, dict[str, str | None]]
        Parsed df and updated formats.
    """
    if df.empty:
        return df, date_formats

    updated = dict(date_formats)

    for col in DT_COLS:
        if col not in df.columns:
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
    df = enforce_epiweek_from_dt_notific(df)
    return df, updated_formats


def week_from_epiweek_string(value: str) -> int | None:
    """
    Convert string epiweek representation to week number (1..53).

    Parameters
    ----------
    value : str
        Value like "2026W04" or "202604" depending on producer.

    Returns
    -------
    int | None
        Week number, or None if not parseable.
    """
    try:
        return Week.fromstring(str(value)).week
    except Exception:
        return None
