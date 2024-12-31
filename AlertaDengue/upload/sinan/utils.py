import numpy as np
import pandas as pd
import datetime as dt
from typing import Iterator, Tuple, Optional, Union


from dados.dbdata import add_dv, calculate_digit


def chunk_gen(chunksize: int, totalsize: int) -> Iterator[Tuple[int, int]]:
    chunks = totalsize // chunksize
    for i in range(chunks):
        yield i * chunksize, (i + 1) * chunksize
    rest = totalsize % chunksize
    if rest:
        yield chunks * chunksize, chunks * chunksize + rest


@np.vectorize
def convert_date(col: Union[pd.Series, dt.datetime]) -> Optional[pd.Series]:
    if pd.isnull(col):
        return None
    else:
        return pd.to_datetime(col).to_pydatetime().date()


@np.vectorize
def convert_nu_ano(year: str, col: pd.Series) -> int:
    return int(year) if pd.isnull(col) else int(col)


@np.vectorize
def convert_sem_pri(col: str) -> int:
    if col:
        col = str(col)[-2:]
    return int(col)


@np.vectorize
def fix_nu_notif(value: Optional[str] = None) -> Optional[int]:
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
