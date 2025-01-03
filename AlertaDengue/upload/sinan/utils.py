import numpy as np
import pandas as pd
import datetime as dt
from typing import Iterator, Tuple, Optional, Union


from dados.dbdata import calculate_digit


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
def convert_date(col: Union[pd.Timestamp, str, None]) -> Optional[dt.date]:
    try:
        if pd.isnull(col):
            return None
        if isinstance(col, dt.date):
            return col
        return pd.to_datetime(col).date()
    except Exception:
        return None


@np.vectorize
def convert_nu_ano(year: str, col: pd.Series) -> int:
    return int(year) if pd.isnull(col) else int(col)


@np.vectorize
def convert_sem_pri(col: str) -> int:
    if col:
        col = str(col)[-2:]
    return int(col)


def fix_nu_notif(value: Union[str, None]) -> Optional[int]:
    char_to_replace = {",": "", "'": "", ".": ""}
    try:
        return int(value)
    except ValueError:
        for char, replacement in char_to_replace.items():
            value = str(value).replace(char, replacement)

        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    except TypeError:
        return None


@np.vectorize
def fill_id_agravo(cid: str, default_cid: str) -> str:
    return default_cid if not cid else cid


@np.vectorize
def convert_sem_not(col: np.ndarray[int]) -> np.ndarray[int]:
    return int(str(int(col))[-2:])


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


def parse_data(df: pd.DataFrame, default_cid: str, year: int) -> pd.DataFrame:
    df["NU_NOTIFIC"] = fix_nu_notif(df.NU_NOTIFIC)
    df["ID_MUNICIP"] = add_dv(df.ID_MUNICIP)

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

    for dt_col in dt_cols:
        df[dt_col] = convert_date(df[dt_col])

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
