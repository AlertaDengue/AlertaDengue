import glob
import logging
from pathlib import Path
from typing import List, Union

import dask.dataframe as dd
import geopandas as gpd
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from simpledbf import Dbf5

logger = logging.getLogger(__name__)


DBFS_PQTDIR = Path(settings.TEMP_FILES_DIR) / "dbfs_parquet"


EXPECTED_FIELDS = [
    "NU_ANO",
    "ID_MUNICIP",
    "ID_AGRAVO",
    "DT_SIN_PRI",
    "SEM_PRI",
    "DT_NOTIFIC",
    "NU_NOTIFIC",
    "SEM_NOT",
    "DT_DIGITA",
    "DT_NASC",
    "NU_IDADE_N",
    "CS_SEXO",
]
SYNONYMS_FIELDS = {"ID_MUNICIP": ["ID_MN_RESI"]}

EXPECTED_DATE_FIELDS = ["DT_SIN_PRI", "DT_NOTIFIC", "DT_DIGITA", "DT_NASC"]

FIELD_MAP = {
    "dt_notific": "DT_NOTIFIC",
    "se_notif": "SEM_NOT",
    "ano_notif": "NU_ANO",
    "dt_sin_pri": "DT_SIN_PRI",
    "se_sin_pri": "SEM_PRI",
    "dt_digita": "DT_DIGITA",
    "municipio_geocodigo": "ID_MUNICIP",
    "nu_notific": "NU_NOTIFIC",
    "cid10_codigo": "ID_AGRAVO",
    "dt_nasc": "DT_NASC",
    "cs_sexo": "CS_SEXO",
    "nu_idade_n": "NU_IDADE_N",
    "resul_pcr": "RESUL_PCR_",
    "criterio": "CRITERIO",
    "classi_fin": "CLASSI_FIN",
}


def calculate_digit(dig: str) -> int:
    """
    Calculates the verifier digit of the municipality geocode.
    Parameters
    ----------
        geocode: str
            IBGE codes of municipalities in Brazil.
    Returns
    -------
        digit: the verifier digit.
    """

    peso = [1, 2, 1, 2, 1, 2, 0]
    soma = 0
    dig = str(dig)
    for i in range(6):
        valor = int(dig[i]) * peso[i]
        soma += sum([int(d) for d in str(valor)]) if valor > 9 else valor
    dv = 0 if soma % 10 == 0 else (10 - (soma % 10))
    return dv


@np.vectorize
def add_dv(geocode: str) -> int:
    """
    Returns the geocode of the municipality by adding the verifier digit.
    If the input geocode is already 7 digits long, it is returned as is.
    If the input geocode is 6 digits long, the verifier digit is calculated
        and appended to the end.
    If the input geocode is 0 digits long, a log message is printed
        and 0 is returned.
    Parameters
    ----------
        geocode: IBGE codes of municipalities in Brazil.
    Returns
    -------
        geocode: geocode 7 digit.
    """

    if len(str(geocode)) == 7:
        return int(geocode)
    elif len(str(geocode)) == 6:
        return int(str(geocode) + str(calculate_digit(geocode)))
    elif len(str(geocode)) == 0:
        return logger.info(len(geocode))

    raise ValueError(f"geocode:{geocode} does not match!")


@np.vectorize
def fix_nu_notif(value: str) -> int:
    """
    Formats NU_NOTIF field value.
    Parameters
    ----------
        value (str): Value of NU_NOTIF field.
    Returns
    -------
        int: Formatted NU_NOTIF field value.
    Raises:
    -------
        ValueError: If value cannot be converted to int.
    """

    char_to_replace = {",": "", "'": "", ".": ""}

    try:
        value = None if pd.isnull(value) else int(value)
    except ValueError as e:
        if any(x in value for x in list(char_to_replace)):
            # Replace multiple characters.
            value = value.translate(str.maketrans(char_to_replace))
        else:
            logger.error(e)

    return value


@np.vectorize
def convert_data_types(col: any, dtype: type) -> any:
    """
    Converts column data types to the specified type.
    Parameters
    ----------
        col (any): The column to convert.
        dtype (type): The data type to convert the column to.
    Returns
    -------
        any: The converted column.
    """

    if pd.isnull(col):
        return None
    elif dtype == str:
        return str(col)
    elif dtype == int:
        return int(col or 0)
    else:
        return dtype.type(col)


@np.vectorize
def fill_id_agravo(col: np.ndarray, default_cid: str) -> np.ndarray:
    """
    Fills missing values in col with default_cid.
    Parameters
    ----------
        col (np.ndarray): A numpy array with missing values.
        default_cid (str): A default value to fill in the missing values.
    Returns
    -------
        np.ndarray: A numpy array with missing values filled using default_cid.
    """

    if col is None:
        if default_cid is None:
            raise ValidationError(
                _(
                    "Existem nesse arquivo notificações que não incluem "
                    "a coluna ID_AGRAVO."
                )
            )
        else:
            return default_cid
    else:
        return col


@np.vectorize
def convert_date(col: Union[pd.Series, np.ndarray]) -> np.ndarray:
    """
    Convert a column of dates to datetime.date objects.

    Parameters
    ----------
    col : Union[pd.Series, np.ndarray]
        A pandas.Series or numpy.ndarray containing date strings.

    Returns
    -------
    np.ndarray
        A numpy.ndarray of datetime.date objects.
    """

    if pd.isnull(col):
        return None
    else:
        return pd.Timestamp(col).to_pydatetime().date()


@np.vectorize
def convert_sem_not(col: np.ndarray) -> np.ndarray:
    """
    Converts a given column of integers to its last two digits.
    Parameters
    ----------
        col (numpy.ndarray): A column of integers to be converted.
    Returns
    -------
        numpy.ndarray: A column of integers with only its last two digits.
    """

    return int(str(int(col))[-2:])


@np.vectorize
def convert_nu_ano(ano: str, col: pd.Series) -> np.ndarray:
    """
    Convert the given 'ano' string to an integer if 'col' is NaN,
    otherwise convert 'col' to an integer.
    Parameters
    ----------
        ano: A string representing the year.
        col: A pandas series representing a column of a dataframe.
    Returns
    -------
        A numpy array of integers.
    """

    return int(ano) if pd.isnull(col) else int(col)


@np.vectorize
def convert_sem_pri(col: str) -> int:
    """
    Converts a column of data from a string to an integer representing
    the last two digits of the string.
    Parameters
    ----------
        col (str): A column of data.
    Returns
    -------
        int: The last two digits of the string as an integer.

    """

    if not col:
        return None
    else:
        return int(str(col)[-2:])


def parse_data(df: pd.DataFrame, default_cid: str, ano: int) -> pd.DataFrame:
    """
    Parse and convert data types for COVID-19 notification data.
    Parameters
    ----------
        df (pandas.core.frame.DataFrame): The dataframe to parse.
        default_cid (str): The default CID code.
        ano (int): The year of the notification data.
    Returns
    -------
        pandas.core.frame.DataFrame: The parsed dataframe.
    """

    df["NU_NOTIFIC"] = fix_nu_notif(df.NU_NOTIFIC)

    df["ID_MUNICIP"] = add_dv(df.ID_MUNICIP)

    df["DT_SIN_PRI"] = convert_date(df.DT_SIN_PRI)
    df["DT_DIGITA"] = convert_date(df.DT_DIGITA)
    df["DT_NASC"] = convert_date(df.DT_NASC)
    df["DT_NOTIFIC"] = convert_date(df.DT_NOTIFIC)

    # Replace values other than 'M' or 'F' with 'I'
    df["CS_SEXO"] = np.where(
        df["CS_SEXO"].isin(["M", "F"]), df["CS_SEXO"], "I"
    ).astype(str)

    df["NU_IDADE_N"] = convert_data_types(df.NU_IDADE_N, int)

    if "RESUL_PCR_" in df.columns:
        df["RESUL_PCR_"] = convert_data_types(
            df.RESUL_PCR_.fillna(value=0), int
        )
    else:
        df["RESUL_PCR_"] = 0

    if "CRITERIO" in df.columns:
        df["CRITERIO"] = convert_data_types(df.CRITERIO.fillna(value=0), int)
    else:
        df["CRITERIO"] = 0

    if "CLASSI_FIN" in df.columns:
        df["CLASSI_FIN"] = convert_data_types(
            df.CLASSI_FIN.fillna(value=0), int
        )
    else:
        df["CLASSI_FIN"] = 0

    df["ID_AGRAVO"] = fill_id_agravo(df.ID_AGRAVO, default_cid)

    df["SEM_PRI"] = convert_sem_pri(df.SEM_PRI)

    df["NU_ANO"] = convert_nu_ano(ano, df.NU_ANO)

    df["SEM_NOT"] = convert_sem_not(df.SEM_NOT)

    return df


def _parse_fields(dbf_name: str, df: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Rename columns and set type datetime when startswith "DT"
    Parameters
    ----------
    dbf_name : str
        Name of the DBF file.
    df : gpd.GeoDataFrame
        GeoDataFrame containing the data.
    Returns
    -------
    pd.DataFrame
        DataFrame with renamed columns and converted datetime columns.
    """
    if "ID_MUNICIP" in df.columns:
        df = df.dropna(subset=["ID_MUNICIP"])
    elif "ID_MN_RESI" in df.columns:
        df = df.dropna(subset=["ID_MN_RESI"])
        df["ID_MUNICIP"] = df.ID_MN_RESI
        del df["ID_MN_RESI"]

    for col in filter(lambda x: x.startswith("DT"), df.columns):
        try:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        except ValueError:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


# def fill_missing_columns(df, col_names: List[str]) -> None:
#     """
#     Check if the table to be inserted contains all columns
#         required in the database model.
#     If not, create these columns filled with Null values to allow
#         for database insertion.
#     Parameters
#     ----------
#     col_names : numpy.ndarray
#         A numpy array of column names to check.
#     Returns
#     -------
#     None
#     """

#     for nm in col_names:
#         if FIELD_MAP[nm] not in df.columns:
#             df[FIELD_MAP[nm]] = None


def select_expected_fields(dbf_name: str) -> List[str]:
    """
    Selects the expected fields based on the fname.
    Parameters
    ----------
    dbf_name : str
        The filename used to determine the expected fields.
    Returns
    -------
    List[str]
        The list of expected fields.
    Notes
    -----
    The function checks the dbf_name to determine the expected fields.
    If dbf_name starts with "BR-DEN" or "BR-CHIK", additional fields
    "RESUL_PCR_", "CRITERIO", and "CLASSI_FIN" are included.
    If dbf_name starts with "BR-ZIKA", fields "CRITERIO" and "CLASSI_FIN"
    are included. For other cases, the list of expected fields remains
    unchanged.
    """
    all_expected_fields = EXPECTED_FIELDS.copy()

    if dbf_name.startswith(("BR-DEN", "BR-CHIK")):
        all_expected_fields.extend(["RESUL_PCR_", "CRITERIO", "CLASSI_FIN"])
    elif dbf_name.startswith(("BR-ZIKA")):
        all_expected_fields.extend(["CRITERIO", "CLASSI_FIN"])

    return all_expected_fields


'''
def drop_duplicates_from_dataframe(
    df: pd.DataFrame, subset: List[str]
    ) -> pd.DataFrame:
    """
    Removes duplicated rows from a pandas DataFrame
    based on a given subset of columns.

    Parameters
    ----------
    df : pd.DataFrame
        The pandas DataFrame to remove duplicates from
    subset : List[str]
        The subset of columns to check for duplicates

    Returns
    -------
    pd.DataFrame
        A pandas DataFrame with duplicated rows removed
    """

    drop_mask = df.duplicated(subset=subset)
    dropped_data = df[drop_mask]
    dropped_count = dropped_data.shape[0]
    dropped_data.to_csv("duplicate_values.csv")
    if dropped_count > 0:
        logger.info(f"Dropped {dropped_count} rows due to duplicate values.")

    df = df[~drop_mask]

    return df
'''


def chunk_gen(chunksize: int, totalsize: int):
    """
    Create chunks.
    Parameters
    ----------
    chunksize : int
        Size of each chunk.
    totalsize : int
        Total size of the data.
    Yields
    ------
    tuple
        A tuple containing the lowerbound and upperbound indices of each chunk.
    """
    chunks = totalsize // chunksize

    for i in range(chunks):
        yield i * chunksize, (i + 1) * chunksize

    rest = totalsize % chunksize

    if rest:
        yield chunks * chunksize, chunks * chunksize + rest


def read_dbf(fname: str) -> pd.DataFrame:
    """
    Generator to read the DBF in chunks.
    Filtering columns from the field_map dictionary on DataFrame and export
    to parquet files.
    Parameters
    ----------
    fname : str
        Path to the DBF file.
    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the DBF file.
    """
    dbf = Dbf5(fname, codec="iso-8859-1")
    dbf_name = str(dbf.dbf)[:-4]
    parquet_dir = Path(DBFS_PQTDIR / f"{dbf_name}.parquet")

    if not parquet_dir.is_dir():
        logger.info("Converting DBF file to Parquet format...")
        Path.mkdir(parquet_dir, parents=True, exist_ok=True)
        for chunk, (lowerbound, upperbound) in enumerate(
            chunk_gen(1000, dbf.numrec)
        ):
            parquet_fname = f"{parquet_dir}/{dbf_name}-{chunk}.parquet"
            df = gpd.read_file(
                fname,
                include_fields=select_expected_fields(dbf_name),
                rows=slice(lowerbound, upperbound),
                ignore_geometry=True,
            )
            df = _parse_fields(dbf_name, df)

            # Remove duplicate rows
            """
            subset_columns = [
                "ID_AGRAVO",
                "ID_MUNICIP",
                "NU_NOTIFIC",
                "SEM_NOT",
            ]
            df = drop_duplicates_from_dataframe(df, subset_columns)
            """

            df.to_parquet(parquet_fname)

    fetch_pq_fname = glob.glob(f"{parquet_dir}/*.parquet")
    chunks_list = [
        dd.read_parquet(f, engine="fastparquet") for f in fetch_pq_fname
    ]

    logger.info("Concatenating the chunks...")
    return dd.concat(chunks_list, ignore_index=True).compute()
