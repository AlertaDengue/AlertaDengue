from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import ForwardRef, Iterable, Iterator, Optional, Tuple, Union

import numpy as np
import pandas as pd
from dados.dbdata import calculate_digit
from dateutil.parser import parse
from epiweeks import Week
from pandas.tseries.api import guess_datetime_format

SINANUpload = ForwardRef("SINANUpload")


UF_CODES = {
    "AC": 12,
    "AL": 27,
    "AM": 13,
    "AP": 16,
    "BA": 29,
    "CE": 23,
    "DF": 53,
    "ES": 32,
    "GO": 52,
    "MA": 21,
    "MG": 31,
    "MS": 50,
    "MT": 51,
    "PA": 15,
    "PB": 25,
    "PE": 26,
    "PI": 22,
    "PR": 41,
    "RJ": 33,
    "RN": 24,
    "RO": 11,
    "RR": 14,
    "RS": 43,
    "SC": 42,
    "SE": 28,
    "SP": 35,
    "TO": 17,
}


def chunk_gen(chunksize: int, totalsize: int) -> Iterator[tuple[int, int]]:

    chunks = totalsize // chunksize
    for i in range(chunks):
        yield i * chunksize, (i + 1) * chunksize

    rest = totalsize % chunksize
    if rest:
        yield chunks * chunksize, chunks * chunksize + rest


@np.vectorize
def add_dv(geocodigo):
    miscalculated_geocodes = {
        "2201911": 2201919,
        "2201986": 2201988,
        "2202257": 2202251,
        "2611531": 2611533,
        "3117835": 3117836,
        "3152139": 3152131,
        "4305876": 4305871,
        "5203963": 5203962,
        "5203930": 5203939,
    }

    try:
        if len(str(geocodigo)) == 7:
            return int(geocodigo)
        elif len(str(geocodigo)) == 6:
            geocode = int(str(geocodigo) + str(calculate_digit(geocodigo)))
            if str(geocode) in miscalculated_geocodes:
                return miscalculated_geocodes[str(geocode)]
            return int(geocode)
        else:
            return None
    except (ValueError, TypeError):
        return None


def convert_date(
    col: Union[pd.Timestamp, str, None], fmt: Optional[str] = None
) -> Optional[dt.date]:
    """Convert a value to ``datetime.date`` or None."""
    try:
        if pd.isnull(col):
            return None
        if isinstance(col, dt.date):
            return col
        try:
            return pd.to_datetime(col, format=fmt).date()
        except ValueError:
            return None
    except Exception:
        return None


def convert_nu_ano(year: int, col: pd.Series) -> int:
    """Fill missing NU_ANO with the run year."""
    return int(year) if pd.isnull(col) else int(col)


@np.vectorize
def convert_sem_pri(val: object) -> int | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    tail = s[-2:] if len(s) >= 2 else ""
    if tail.isdigit():
        return int(tail)
    return None


@np.vectorize
def fix_nu_notif(value: Union[str, None]) -> Optional[int]:
    char_to_replace = {",": "", "'": "", ".": ""}
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        for char, replacement in char_to_replace.items():
            value = value.replace(char, replacement)
        try:
            return int(value)
        except ValueError:
            return None


@np.vectorize
def fill_id_agravo(cid: str, default_cid: str) -> str:
    return default_cid if not cid else cid


@np.vectorize
def convert_sem_not(val: object) -> int | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    tail = s[-2:] if len(s) >= 2 else ""
    if tail.isdigit():
        return int(tail)
    return None


def is_date_ambiguous(value: str) -> bool:
    """
    Determine if a date string is ambiguous for inferring its format.
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
    """Infer the most common date format in a collection of strings."""
    dates = [d for d in set(values) if d and not is_date_ambiguous(d)]
    scores = Counter(
        fmt
        for fmt in (guess_datetime_format(d) for d in dates)
        if fmt is not None
    )
    return scores.most_common(1)[0][0] if scores else None


def parse_dt_notific_with_sem_not(
    dt_notific: pd.Series,
    sem_not: pd.Series,
) -> pd.Series:
    """Parse DT_NOTIFIC choosing between YYYY-MM-DD and YYYY-DD-MM using SEM_NOT.

    SEM_NOT in SINAN is based on the SINAN epiweek calendar (Sunday-Saturday
    + 4+ days rule). This function matches candidates against SEM_NOT using
    the same SINAN calendar.
    """
    raw = dt_notific.astype("string").str.strip()
    a = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")
    b = pd.to_datetime(raw, format="%Y-%d-%m", errors="coerce")

    s = sem_not.astype("string").str.strip()
    sem_y = pd.to_numeric(s.str.slice(0, 4), errors="coerce").astype("Int64")
    sem_w = pd.to_numeric(s.str.slice(4, 6), errors="coerce").astype("Int64")
    sem_code = (sem_y * 100 + sem_w).astype("Int64")

    a_y, a_w = _sinan_year_week_from_ts(a)
    b_y, b_w = _sinan_year_week_from_ts(b)
    a_code = (a_y * 100 + a_w).astype("Int64")
    b_code = (b_y * 100 + b_w).astype("Int64")

    a_dist = (a_code - sem_code).abs()
    b_dist = (b_code - sem_code).abs()

    has_sem = sem_code.notna()
    choose_b = b.notna() & (a.isna() | (has_sem & (b_dist < a_dist)))

    chosen = a.where(~choose_b, b)
    out = chosen.dt.date
    return out.where(chosen.notna(), None)


def _to_py_int(value: object) -> int | None:
    """
    Convert a scalar to Python int, preserving missing as None.

    Parameters
    ----------
    value
        Scalar value.

    Returns
    -------
    int | None
        Python int if value is not missing, otherwise None.
    """
    if pd.isna(value):
        return None
    return int(value)


def _sinan_year_week_from_ts(
    ts: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """
    Compute SINAN epidemiological (year, week) from timestamps.

    SINAN rule (CDC epiweek):
    - Week starts on Sunday and ends on Saturday.
    - Week-year is the year that contains at least 4 days of that epiweek.
    - Week 1 is the week that contains January 4th.

    Parameters
    ----------
    ts
        Datetime-like pandas Series.

    Returns
    -------
    tuple[pd.Series, pd.Series]
        (year, week) as nullable Int64 series.
    """
    dt_ts = pd.to_datetime(ts, errors="coerce")
    mask = dt_ts.notna()

    out_year = pd.Series(pd.NA, index=ts.index, dtype="Int64")
    out_week = pd.Series(pd.NA, index=ts.index, dtype="Int64")
    if not bool(mask.any()):
        return out_year, out_week

    weekday = dt_ts.dt.weekday
    offset = (weekday + 1) % 7
    week_start = dt_ts - pd.to_timedelta(offset, unit="D")
    week_end = week_start + pd.to_timedelta(6, unit="D")

    start_year = week_start.dt.year.astype("Int64")
    end_year = week_end.dt.year.astype("Int64")

    crosses = start_year != end_year
    end_of_start_year = pd.to_datetime(
        start_year.astype("string") + "-12-31",
        errors="coerce",
    )

    days_in_start_year = pd.Series(7, index=ts.index, dtype="Int64")
    days_in_start_year = days_in_start_year.where(
        ~crosses,
        (end_of_start_year - week_start).dt.days.astype("Int64") + 1,
    )

    week_year = start_year.where(
        ~crosses | (days_in_start_year >= 4),
        end_year,
    )

    jan4 = pd.to_datetime(
        week_year.astype("string") + "-01-04",
        errors="coerce",
    )
    jan4_weekday = jan4.dt.weekday
    jan4_offset = (jan4_weekday + 1) % 7
    first_week_start = jan4 - pd.to_timedelta(jan4_offset, unit="D")

    week_no = ((week_start - first_week_start).dt.days // 7) + 1

    out_year.loc[mask] = week_year.loc[mask].astype("Int64")
    out_week.loc[mask] = week_no.loc[mask].astype("Int64")

    return out_year, out_week


def derive_epiweek_from_dt_notific(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce (NU_ANO, SEM_NOT) derived from DT_NOTIFIC using SINAN calendar.

    Parameters
    ----------
    df
        Parsed chunk dataframe.

    Returns
    -------
    pd.DataFrame
        Dataframe with NU_ANO/SEM_NOT consistent with DT_NOTIFIC.
    """
    if "DT_NOTIFIC" not in df.columns:
        return df

    dt_ts = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce")
    mask = dt_ts.notna()
    if not bool(mask.any()):
        return df

    year, week = _sinan_year_week_from_ts(dt_ts)
    ok = year.notna() & week.notna()

    if "NU_ANO" in df.columns:
        df.loc[ok, "NU_ANO"] = year.loc[ok]
        df["NU_ANO"] = df["NU_ANO"].map(_to_py_int)

    if "SEM_NOT" in df.columns:
        df.loc[ok, "SEM_NOT"] = week.loc[ok]
        df["SEM_NOT"] = df["SEM_NOT"].map(_to_py_int)

    return df


def normalize_cid10(value: object, default_cid: str) -> str:
    """Normalize CID10 codes for dengue/chikungunya/zika only.

    Parameters
    ----------
    value
        Raw CID10 value (e.g. ``A920``, ``A92.0``, ``A92.8``, ``A90.0``).
    default_cid
        Default CID10 for the current ingestion run.

    Returns
    -------
    str
        Canonical CID10 code. For the supported diseases:
        - dengue: ``A90``
        - chikungunya: ``A92.0``
        - zika: ``A928``

        Any other code is returned mostly unchanged (uppercased/trimmed).
    """
    if pd.isna(value):
        raw = ""
    else:
        raw = str(value)

    code = raw.strip().upper().replace(" ", "")
    fallback = str(default_cid).strip().upper().replace(" ", "")

    if not code:
        code = fallback

    variants: dict[str, str] = {
        "A90": "A90",
        "A90.0": "A90",
        "A92.": "A92.0",
        "A92.0": "A92.0",
        "A920": "A92.0",
        "A92.8": "A928",
        "A928": "A928",
    }

    normalized = variants.get(code)
    if normalized is not None:
        return normalized

    fallback_normalized = variants.get(fallback)
    if fallback_normalized is not None:
        return code[:5]

    return code[:5]


def convert_data_types(col: pd.Series, dtype: type) -> pd.Series:
    if dtype == int:
        col = pd.to_numeric(col, errors="coerce").fillna(0).astype(int)
    elif dtype == float:
        col = pd.to_numeric(col, errors="coerce").fillna(0.0)
    elif dtype == str:
        col = col.fillna("").astype(str)
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")
    return col


def parse_dates(df: pd.DataFrame, sinan: SINANUpload) -> pd.DataFrame:
    """
    Parse SINAN date columns, keeping best-effort format tracking.

    Parameters
    ----------
    df
        Chunk dataframe.
    sinan
        Upload model instance with persisted formats.

    Returns
    -------
    pd.DataFrame
        Parsed dataframe.
    """
    dt_cols = [
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
    formats: dict[str, str | None] = {}
    sinan_formats = sinan.date_formats or {}

    if df.empty:
        return df

    if "DT_NOTIFIC" in df.columns:
        if "SEM_NOT" in df.columns:
            df["DT_NOTIFIC"] = parse_dt_notific_with_sem_not(
                df["DT_NOTIFIC"],
                df["SEM_NOT"],
            )
        else:
            fmt: str | None = None
            if df["DT_NOTIFIC"].dtype == "object":
                fmt = infer_date_format(df["DT_NOTIFIC"].astype(str).tolist())
                formats["DT_NOTIFIC"] = fmt
            df["DT_NOTIFIC"] = convert_date(df["DT_NOTIFIC"], fmt)

    for dt_col in dt_cols:
        if dt_col not in df.columns or dt_col == "DT_NOTIFIC":
            continue

        fmt = None
        if df[dt_col].dtype == "object":
            fmt = infer_date_format(df[dt_col].astype(str).tolist())
            formats[dt_col] = fmt

        df[dt_col] = convert_date(df[dt_col], fmt)

    for col, fmt in formats.items():
        if col not in sinan_formats:
            sinan_formats[col] = fmt

        if not sinan_formats[col]:
            sinan_formats[col] = fmt

        if fmt and sinan_formats[col] != fmt:
            sinan.status.warning(
                f"A date discrepancy were found for the column {col}. "
                "Please contact the moderation"
            )
            sinan.status.debug(
                f"DATE FORMAT CHANGED FROM '{sinan_formats[col]}' TO '{fmt}'"
            )
            sinan_formats[col] = fmt

    if sinan.date_formats != sinan_formats:
        sinan.date_formats = sinan_formats
        sinan.save()

    return df


def parse_data(df: pd.DataFrame, default_cid: str, year: int) -> pd.DataFrame:
    """
    Normalize SINAN fields and coerce types.

    Parameters
    ----------
    df
        Chunk dataframe.
    default_cid
        Default CID10.
    year
        Run year (fallback for NU_ANO).

    Returns
    -------
    pd.DataFrame
        Normalized dataframe.
    """
    if df.empty:
        return df

    df["NU_NOTIFIC"] = fix_nu_notif(df["NU_NOTIFIC"])
    df["ID_MUNICIP"] = add_dv(df["ID_MUNICIP"])

    df["CS_SEXO"] = np.where(
        df["CS_SEXO"].isin(["M", "F"]), df["CS_SEXO"], "I"
    ).astype(str)

    int_cols = [
        "NU_IDADE_N",
        "ID_DISTRIT",
        "ID_BAIRRO",
        "ID_UNIDADE",
    ]

    for int_col in int_cols:
        if int_col in df.columns:
            df[int_col] = convert_data_types(df[int_col], int)

    if "RESUL_PCR_" in df.columns:
        df["RESUL_PCR_"] = convert_data_types(df["RESUL_PCR_"], int)
    else:
        df["RESUL_PCR_"] = 0

    if "CRITERIO" in df.columns:
        df["CRITERIO"] = convert_data_types(df["CRITERIO"], int)
    else:
        df["CRITERIO"] = 0

    if "CLASSI_FIN" in df.columns:
        df["CLASSI_FIN"] = convert_data_types(df["CLASSI_FIN"], int)
    else:
        df["CLASSI_FIN"] = 0

    df["ID_AGRAVO"] = fill_id_agravo(df["ID_AGRAVO"], default_cid)
    df["ID_AGRAVO"] = df["ID_AGRAVO"].apply(
        lambda v: normalize_cid10(v, default_cid=default_cid)
    )

    df["SEM_PRI"] = df["SEM_PRI"].apply(convert_sem_pri)
    df["NU_ANO"] = convert_nu_ano(year, df["NU_ANO"])
    df["SEM_NOT"] = df["SEM_NOT"].apply(convert_sem_not)

    return df
