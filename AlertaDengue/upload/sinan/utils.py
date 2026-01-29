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


def chunk_gen(chunksize: int, totalsize: int) -> Iterator[Tuple[int, int]]:
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


@np.vectorize
def convert_date(
    col: Union[pd.Timestamp, str, None], fmt: Optional[str] = None
) -> Optional[dt.date]:
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


@np.vectorize
def convert_nu_ano(year: str, col: pd.Series) -> int:
    return int(year) if pd.isnull(col) else int(col)


@np.vectorize
def convert_sem_pri(val: str) -> int | None:
    if pd.isna(val):
        return pd.NA
    try:
        return Week.fromstring(str(val)).week
    except (ValueError, AttributeError, TypeError):
        return pd.NA


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
def convert_sem_not(val: np.ndarray[int]) -> np.ndarray[int] | None:
    if pd.isna(val):
        return pd.NA
    try:
        return Week.fromstring(str(val)).week
    except (ValueError, AttributeError, TypeError):
        return pd.NA


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


def parse_dt_notific_with_sem_not(
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

    s = sem_not.astype("string").str.strip()
    extracted = s.str.extract(r"(?P<y>\d{4}).*?(?P<w>\d{2})$")
    sem_y = pd.to_numeric(extracted["y"], errors="coerce").astype("Int64")
    sem_w = pd.to_numeric(extracted["w"], errors="coerce").astype("Int64")
    sem_code = (sem_y * 100 + sem_w).astype("Int64")

    a_iso = a.dt.isocalendar()
    b_iso = b.dt.isocalendar()
    a_code = a_iso.year.astype("Int64") * 100 + a_iso.week.astype("Int64")
    b_code = b_iso.year.astype("Int64") * 100 + b_iso.week.astype("Int64")

    a_dist = (a_code - sem_code).abs()
    b_dist = (b_code - sem_code).abs()

    has_sem = sem_code.notna()
    choose_b = b.notna() & (a.isna() | (has_sem & (b_dist < a_dist)))

    chosen = a.where(~choose_b, b)
    out = chosen.dt.date
    return out.where(chosen.notna(), None)


def derive_epiweek_from_dt_notific(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enforce (NU_ANO, SEM_NOT) derived from DT_NOTIFIC when present.

    Parameters
    ----------
    df
        Chunk dataframe after parsing.

    Returns
    -------
    pd.DataFrame
        Dataframe with consistent NU_ANO and SEM_NOT.
    """
    if "DT_NOTIFIC" not in df.columns:
        return df

    dt_ts = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce")
    mask = dt_ts.notna()
    if not bool(mask.any()):
        return df

    iso = dt_ts.dt.isocalendar()
    if "NU_ANO" in df.columns:
        df.loc[mask, "NU_ANO"] = iso.year.astype("Int64")[mask]
    if "SEM_NOT" in df.columns:
        df.loc[mask, "SEM_NOT"] = iso.week.astype("Int64")[mask]

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

    if "DT_NOTIFIC" in df.columns and "SEM_NOT" in df.columns:
        df["DT_NOTIFIC"] = parse_dt_notific_with_sem_not(
            df["DT_NOTIFIC"],
            df["SEM_NOT"],
        )

    for dt_col in dt_cols:
        if dt_col not in df.columns:
            continue
        if dt_col == "DT_NOTIFIC":
            continue

        fmt: str | None = None
        if df[dt_col].dtype == "object":
            fmt = infer_date_format(df[dt_col])
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
    df["NU_NOTIFIC"] = fix_nu_notif(df.NU_NOTIFIC)
    df["ID_MUNICIP"] = add_dv(df.ID_MUNICIP)

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
        df[int_col] = convert_data_types(df[int_col], int)

    df["RESUL_PCR_"] = (
        convert_data_types(df["RESUL_PCR_"], int)
        if "RESUL_PCR_" in df.columns
        else 0
    )
    df["CRITERIO"] = (
        convert_data_types(df["CRITERIO"], int)
        if "CRITERIO" in df.columns
        else 0
    )
    df["CLASSI_FIN"] = (
        convert_data_types(df["CLASSI_FIN"], int)
        if "CLASSI_FIN" in df.columns
        else 0
    )

    df["ID_AGRAVO"] = fill_id_agravo(df.ID_AGRAVO, default_cid)
    df["ID_AGRAVO"] = df["ID_AGRAVO"].apply(
        lambda v: normalize_cid10(v, default_cid=default_cid)
    )

    df["SEM_PRI"] = df["SEM_PRI"].apply(convert_sem_pri)
    df["NU_ANO"] = convert_nu_ano(year, df.NU_ANO)
    df["SEM_NOT"] = df["SEM_NOT"].apply(convert_sem_not)

    return df
