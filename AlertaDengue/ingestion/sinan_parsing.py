from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Iterable

import pandas as pd
from dateutil.parser import parse
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


def is_date_ambiguous(value: str) -> bool:
    """
    Determine if a date string is ambiguous for inferring its format.

    Parameters
    ----------
    value
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
    values
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
            return pd.to_datetime(v, format=fmt, errors="raise").date()
        except Exception:
            return None

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
    extracted = s.str.extract(r"(?P<y>\d{4}).*?(?P<w>\d{2})$")
    year = pd.to_numeric(extracted["y"], errors="coerce").astype("Int64")
    week = pd.to_numeric(extracted["w"], errors="coerce").astype("Int64")
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


def _derive_epiweek_from_dt_notific(df: pd.DataFrame) -> pd.DataFrame:
    if "DT_NOTIFIC" not in df.columns:
        return df

    dt_ts = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce")
    iso = dt_ts.dt.isocalendar()
    mask = dt_ts.notna()

    if "NU_ANO" in df.columns:
        df.loc[mask, "NU_ANO"] = iso.year.astype("Int64")[mask]
    if "SEM_NOT" in df.columns:
        df.loc[mask, "SEM_NOT"] = iso.week.astype("Int64")[mask]

    return df


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
    df = _derive_epiweek_from_dt_notific(df)
    return df, updated_formats
