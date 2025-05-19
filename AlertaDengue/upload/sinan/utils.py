import datetime as dt
from collections import Counter
from typing import ForwardRef, Iterable, Iterator, Optional, Tuple, Union

import numpy as np
import pandas as pd
from dados.dbdata import calculate_digit
from dateutil.parser import parse, parser
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
def convert_sem_pri(col: str) -> int | None:
    try:
        return int(str(col)[-2:])
    except ValueError:
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
def convert_sem_not(col: np.ndarray[int]) -> np.ndarray[int] | None:
    try:
        return int(str(int(col))[-2:])
    except ValueError:
        return None


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
    formats = {}
    sinan_formats = sinan.date_formats or {}

    if df.empty:
        return df

    for dt_col in dt_cols:
        fmt = None
        if dt_col in df.columns:
            if df[dt_col].dtype == "object":
                fmt = infer_date_format(df[dt_col])
                formats[dt_col] = fmt
            df[dt_col] = convert_date(df[dt_col], fmt)

    for col, fmt in formats.items():
        if not col in sinan_formats:
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

    df["SEM_PRI"] = convert_sem_pri(df.SEM_PRI)

    df["NU_ANO"] = convert_nu_ano(year, df.NU_ANO)

    df["SEM_NOT"] = convert_sem_not(df.SEM_NOT)

    return df


def infer_date_format(date_series: Iterable[str]) -> str | None:
    """
    Returns the most common date format found in a series of strings. Returns
    None if it was not possible to infer

    ```
    infer_date_format([None, "abc", "01-20-2020"]) # None (same scores)
    infer_date_format([None, "abc", "01-20-2020", "03-26-2020"]) # '%m-%d-%Y'
    ```

    @param date_series: it must be an Iterable of strings
    """
    dates = [d for d in set(date_series) if not is_date_ambiguous(d)]
    scores = Counter(
        fmt
        for fmt in [guess_datetime_format(d) for d in dates if d]
        if fmt is not None
    )
    return scores.most_common(1)[0][0] if scores else None


def is_date_ambiguous(date: str) -> bool:
    """
    The date is ambiguous when it's format can't be determined.
    How it's being used only to filter out ambiguous dates, value errors can
    be ignored

    Examples:
    12/05/2023 (%m/%d/%Y or %d/%m/%Y)   True
    2023-05-12          ||              True
    12-12-2023          ||              True
    25/03/1999 (can't be %m/%d/%Y)      False
    1999-25-03          ||              False
    """
    try:
        monthfirst = parse(date, dayfirst=False)
        dayfirst = parse(date, dayfirst=True)

        if monthfirst == dayfirst and dayfirst.day != dayfirst.month:
            return False

        if monthfirst.day <= 12:
            return True

        if dayfirst.day <= 12:
            return True

    except (ValueError, TypeError):
        pass

    return False
