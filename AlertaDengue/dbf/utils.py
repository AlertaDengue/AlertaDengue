import datetime as dt
import glob
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple, Union

import dask.dataframe as dd
import geopandas as gpd
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from loguru import logger
from simpledbf import Dbf5

# Directories
temp_files_dir = Path(settings.TEMP_FILES_DIR)
dbf_sinan = Path(settings.DBF_SINAN)
DBF_CSV_DIR = dbf_sinan / "dbf_duplicated_csv"
DBF_PQT_DIR = temp_files_dir / "dbf_parquet"

# Create directories if they don't exist
for directory in [DBF_CSV_DIR, DBF_PQT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

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

    raise ValueError(f"geocode:{geocode} does not match!")


@np.vectorize
def fix_nu_notif(value: Union[str, None]) -> Optional[int]:
    """
    Formats NU_NOTIF field value.
    Parameters
    ----------
        value: Union[str, None]
            Value of NU_NOTIF field.
    Returns
    -------
        Optional[int]: Formatted NU_NOTIF field value.
    Raises
    ------
        ValueError: If value cannot be converted to int.
    """
    char_to_replace = {",": "", "'": "", ".": ""}
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        # Replace multiple characters.
        for char, replacement in char_to_replace.items():
            value = value.replace(char, replacement)

        try:
            return int(value)
        except ValueError:
            logger.error(f"Invalid NU_NOTIF value: {value}")
            return None


@np.vectorize
def convert_data_types(
    col: Union[pd.Series, Any], dtype: type
) -> Optional[Any]:
    """
    Convert the data type of the given column to the specified dtype.
    Parameters
    ----------
        col (Union[pd.Series, Any]): The column to convert.
        dtype (type): The data type to convert the column to.

    Returns
    -------
        Optional[Any]: The converted column, or None if the column is null.
    """
    if pd.isnull(col):
        return None
    elif dtype == str:
        return str(col)
    elif dtype == int:
        return int(col or 0)
    else:
        return dtype(col)


@np.vectorize
def fill_id_agravo(col: str, default_cid: str) -> str:
    """
    Fills missing values in col with default_cid.
    Parameters
    ----------
        col (np.ndarray): A numpy array with missing values.
        default_cid (str): A default value to fill in the missing values.
    Returns
    -------
        str: String with missing values filled using default_cid.
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
def convert_date(col: Union[pd.Series, dt.datetime]) -> Optional[pd.Series]:
    """
    Convert a column of dates to datetime.date objects.
    Parameters
    ----------
    col : Union[pd.Series, np.ndarray]
        A pandas.Series or numpy array containing date strings.

    Returns
    -------
    Optional[np.ndarray]
        A Any of datetime.date objects, or None if the input is null.
    """

    if pd.isnull(col):
        return None
    else:
        return pd.to_datetime(col).to_pydatetime().date()


@np.vectorize
def convert_sem_not(col: np.ndarray[int]) -> np.ndarray[int]:
    """
    Converts a given column of integers to its last two digits.
    Parameters
    ----------
    col : numpy.ndarray[int]
        A column of integers to be converted.
    Returns
    -------
    numpy.ndarray[int]
        A column of integers with only its last two digits.
    """
    return int(str(int(col))[-2:])


@np.vectorize
def convert_nu_ano(year: str, col: pd.Series) -> int:
    """
    Convert the given 'year' string to an integer if 'col' is NaN,
    otherwise convert 'col' to an integer.
    Parameters
    ----------
        year: A string representing the year.
        col: A pandas series representing a column of a dataframe.
    Returns
    -------
        int: A column of integers.
    """

    return int(year) if pd.isnull(col) else int(col)


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

    if col:
        col = str(col)[-2:]

    return int(col)


def parse_data(df: pd.DataFrame, default_cid: str, year: int) -> pd.DataFrame:
    """
    Parse and convert data types for the notification data.
    Parameters
    ----------
        df (pandas.core.frame.DataFrame): The dataframe to parse.
        default_cid (str): The default CID code.
        year (int): The year of the notification data.
    Returns
    -------
        pandas.core.frame.DataFrame: The parsed dataframe.
    """
    logger.info("Parsing rows and converting data types...")

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

    df["NU_ANO"] = convert_nu_ano(year, df.NU_ANO)

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


def list_expected_fields(dbf_fields: List[Tuple[str, str]]) -> List[str]:
    """
    Return a list of expected fields based on the FIELD_MAP and dbf_fields.
    Parameters
    ----------
        dbf_fields (List[tuple]): A list of tuples representing the fields in the dbf file.
    Returns
    -------
        List[str]: A list of expected fields.
    """
    expected_fields = list(FIELD_MAP.values())
    existing_fields = [
        field[0] for field in dbf_fields if field[0] in expected_fields
    ]
    missing_fields = [
        field for field in expected_fields if field not in existing_fields
    ]

    try:
        expected_fields += missing_fields

        if missing_fields:
            expected_fields += existing_fields
            logger.info(
                f"Added {len(missing_fields)} new fields for the DBF columns!"
            )

    except Exception as e:
        logger.error(e)

    return expected_fields


def drop_duplicates_from_dataframe(
    df: pd.DataFrame, default_cid_name: str, year: int
) -> pd.DataFrame:
    """
    Remove duplicates from a pandas DataFrame based on the provided conditions.
    The function checks if the data has duplicate values.
    If the first condition (SEM_NOT) is met, it saves the data to a CSV file
    and returns the original DataFrame without any changes.
    If the second condition (DT_NOTIFIC) is met,
    it drops the duplicate rows from the DataFrame and
    returns it without the duplicate values.
    Parameters
    ----------
    df : pd.DataFrame
        The pandas DataFrame to remove duplicates from.
    Returns
    -------
    pd.DataFrame
        A pandas DataFrame with duplicates removed.
    """
    logger.info("Removing duplicates...")

    duplicate_se_notific_mask = df.duplicated(
        subset=["ID_AGRAVO", "NU_NOTIFIC", "ID_MUNICIP", "SEM_NOT"]
    )
    if duplicate_se_notific_mask.any():
        logger.info("Duplicates found for the same epiweek!")
        df_se_notific = df[duplicate_se_notific_mask]
        df_se_notific.to_csv(
            DBF_CSV_DIR
            / f"duplicate_values_SE_NOT_{year}_{default_cid_name}.csv",
            index=False,
        )
        if df_se_notific.shape[0] > 0:
            logger.info(
                f"Saved {df_se_notific.shape[0]} rows due to duplicate values (Condition SEM_NOT)."  # NOQA E999
            )

    duplicate_dt_notific_mask = df.duplicated(
        subset=["ID_AGRAVO", "NU_NOTIFIC", "ID_MUNICIP", "DT_NOTIFIC"]
    )
    if duplicate_dt_notific_mask.any():
        logger.info("Duplicates found for the same notification date")
        df_dt_notific = df[duplicate_dt_notific_mask]
        df_dt_notific.to_csv(
            DBF_CSV_DIR
            / f"duplicate_values_DT_NOT_{year}_{default_cid_name}.csv",
            index=False,
        )
        if df_dt_notific.shape[0] > 0:
            logger.info(
                f"Saved {df_dt_notific.shape[0]} rows due to duplicate values (Condition DT_NOTIFIC)."  # NOQA E999
            )

        df = df[~duplicate_dt_notific_mask]

    return df


def chunk_gen(chunksize: int, totalsize: int) -> Iterator[Tuple[int, int]]:
    """
    Generate chunks.
    Parameters
    ----------
        chunksize (int): Size of each chunk.
        totalsize (int): Total size of the data.
    Yields
    ------
        Tuple[int, int]: A tuple containing the lowerbound and upperbound indices of each chunk.
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
    dbf_fields = dbf.fields
    expeceted_cols = list_expected_fields(dbf_fields)
    parquet_dir = DBF_PQT_DIR / f"{dbf_name}"

    if not parquet_dir.is_dir():
        logger.info("Converting DBF file to Parquet format...")
        Path.mkdir(parquet_dir, parents=True, exist_ok=True)
        for chunk, (lowerbound, upperbound) in enumerate(
            chunk_gen(1000, dbf.numrec)
        ):
            parquet_fname = f"{parquet_dir}/{dbf_name}-{chunk}.parquet"
            df = gpd.read_file(
                fname,
                include_fields=expeceted_cols,
                rows=slice(lowerbound, upperbound),
                ignore_geometry=True,
            )
            df = _parse_fields(dbf_name, df)
            df.to_parquet(parquet_fname)

    fetch_pq_fname = glob.glob(f"{parquet_dir}/*.parquet")
    if len(fetch_pq_fname) == 0:
        raise ValueError("No Parquet files found in the specified directory.")

    chunks_list = [
        dd.read_parquet(f, engine="fastparquet") for f in fetch_pq_fname
    ]

    logger.info("Concatenating the chunks...")
    return dd.concat(chunks_list, ignore_index=True).compute()
