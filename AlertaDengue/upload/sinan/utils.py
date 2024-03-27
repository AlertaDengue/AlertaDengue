from typing import Optional, Union, Iterator, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
from loguru import logger
from django.utils.translation import gettext_lazy as _

from ad_main import settings

duplicated_sinan_dir = Path(str(settings.DBF_SINAN)) / "duplicated_csvs"
duplicated_sinan_dir.mkdir(parents=True, exist_ok=True)

residue_sinan_dir = Path(str(settings.DBF_SINAN)) / "residue_csvs"
residue_sinan_dir.mkdir(parents=True, exist_ok=True)


EXPECTED_FIELDS = {
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

EXPECTED_DATE_FIELDS = ["DT_SIN_PRI", "DT_NOTIFIC", "DT_DIGITA", "DT_NASC"]

DISEASE_CID = {
    "dengue": "A90",
    "chik": "A92.0",
    "zika": "A98"
}


def sinan_drop_duplicates_from_dataframe(
    df: pd.DataFrame, filename: str
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
    logger.info(f"Removing duplicates from {filename}")

    duplicate_se_notific_mask = df.duplicated(
        subset=["ID_AGRAVO", "NU_NOTIFIC", "ID_MUNICIP", "SEM_NOT"]
    )

    if duplicate_se_notific_mask.any():
        logger.warning("Duplicates found for the same epiweek!")

        df_se_notific = df[duplicate_se_notific_mask]

        if df_se_notific.shape[0] > 0:
            dup_file = (
                duplicated_sinan_dir /
                f"duplicate_values_SE_NOT_{filename}.csv"
            )

            with open(dup_file, "a") as f:
                df_se_notific.to_csv(
                    f,
                    index=False,
                    mode="a",
                    header=(not f.tell())
                )

            logger.info(
                f"Saved {df_se_notific.shape[0]} rows due to duplicate values "
                "(Condition SEM_NOT)."
            )

    duplicate_dt_notific_mask = df.duplicated(
        subset=["ID_AGRAVO", "NU_NOTIFIC", "ID_MUNICIP", "DT_NOTIFIC"]
    )

    if duplicate_dt_notific_mask.any():
        logger.debug("Duplicates found for the same notification date")

        df_dt_notific = df[duplicate_dt_notific_mask]

        dup_file = (
            duplicated_sinan_dir /
            f"duplicate_values_DT_NOT_{filename}.csv"
        )

        with open(dup_file, "a") as f:
            df_dt_notific.to_csv(
                f,
                index=False,
                mode="a",
                header=(not f.tell())
            )

        if df_dt_notific.shape[0] > 0:
            logger.info(
                f"Saved {df_dt_notific.shape[0]} rows due to duplicate values "
                "(Condition DT_NOTIFIC)."
            )

        df = df[~duplicate_dt_notific_mask]  # pyright: ignore

    return df


def sinan_parse_fields(df: pd.DataFrame, sinan_obj) -> pd.DataFrame:
    """
    Rename and parse data types on dataframe columns based on SINAN specs
    Parameters
    ----------
    df : DataFrame
        DataFrame containing the data.
    sinan_obj : SINAN
        SINAN object
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

    for col in filter(lambda x: x in EXPECTED_DATE_FIELDS, df.columns):
        df[col] = df[col].apply(
            lambda row: sinan_parse_date_field(row, sinan_obj)
        )
        df = df.dropna(subset=[col])

    df["NU_NOTIFIC"] = df["NU_NOTIFIC"].apply(fix_nu_notif)
    df["ID_MUNICIP"] = df["ID_MUNICIP"].apply(add_dv)

    df["CS_SEXO"] = np.where(
        df["CS_SEXO"].isin(["M", "F"]), df["CS_SEXO"], "I"
    ).astype(str)

    df["RESUL_PCR_"] = (
        convert_data_types(df["RESUL_PCR_"], int)  # pyright: ignore
        if "RESUL_PCR_" in df.columns
        else 0
    )
    df["CRITERIO"] = (
        convert_data_types(df["CRITERIO"], int)  # pyright: ignore
        if "CRITERIO" in df.columns
        else 0
    )
    df["CLASSI_FIN"] = (
        convert_data_types(df["CLASSI_FIN"], int)  # pyright: ignore
        if "CLASSI_FIN" in df.columns
        else 0
    )

    df["ID_AGRAVO"] = df["ID_AGRAVO"].apply(
        lambda x: fill_id_agravo(x, DISEASE_CID[sinan_obj.disease])
    )

    df["SEM_PRI"] = df["SEM_PRI"].apply(
        lambda x: str(x)[-2:] if x else x
    )

    df["NU_ANO"] = df["NU_ANO"].apply(
        lambda x: sinan_obj.notification_year if pd.isnull(x) else int(x)
    )

    df["SEM_NOT"] = df["SEM_NOT"].apply(lambda x: int(str(int(x))[-2:]))

    return df


def sinan_parse_date_field(value, sinan_obj) -> Optional[pd.Timestamp]:
    try:
        value = pd.to_datetime(value)
    except pd.errors.OutOfBoundsDatetime:
        sinan_obj.parse_error = True

        residue_csv_file = (
            residue_sinan_dir /
            f"RESIDUE_{Path(sinan_obj.filename).with_suffix('.csv')}"
        )

        logger.warning(
            f"Parsing residues found for {sinan_obj.filename}, please check "
            f"{residue_csv_file} manually"
        )

        with open(str(residue_csv_file.absolute()), "a") as f:
            value.to_csv(
                f,
                index=False,
                mode="a",
                header=(not f.tell())
            )

        sinan_obj.error_residue = str(residue_csv_file)
        sinan_obj.save()
        return None

    return value


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
            logger.error(_(f"Invalid NU_NOTIF value: {value}"))
            return None


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

    raise ValueError(_(f"geocode:{geocode} does not match!"))


def convert_data_types(col: pd.Series, dtype: type) -> pd.Series:
    """
    Convert the data type of the given pandas Series to the specified dtype,
    handling missing values appropriately.

    Parameters
    ----------
    col : pd.Series
        The pandas Series to convert.
    dtype : type
        The target data type to convert the Series to. Supported types are `int`, `float`, and `str`.

    Returns
    -------
    pd.Series
        The converted Series with the specified data type.
    """
    if dtype == int:
        # Convert to numeric first to handle strings that represent numbers,
        # NaNs will become float
        col = pd.to_numeric(
            col, errors="coerce"
        ).fillna(0).astype(int)  # pyright: ignore
    elif dtype == float:
        col = pd.to_numeric(
            col, errors="coerce"
        ).fillna(0.0)  # pyright: ignore
    elif dtype == str:
        col = col.fillna("").astype(str)
    else:
        raise ValueError(_(f"Unsupported dtype: {dtype}"))

    return col


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
            raise ValueError(
                _(
                    "Existem nesse arquivo notificações que não incluem "
                    "a coluna ID_AGRAVO."
                )
            )
        else:
            return default_cid
    else:
        return col


def chunk_gen(chunksize: int, totalsize: int) -> Iterator[Tuple[int, int]]:
    """
    Generate chunks.
    Parameters
    ----------
        chunksize (int): Size of each chunk.
        totalsize (int): Total size of the data.
    Yields
    ------
        Tuple[int, int]: A tuple containing the lowerbound and upperbound 
        indices of each chunk.
    """
    chunks = totalsize // chunksize

    for i in range(chunks):
        yield i * chunksize, (i + 1) * chunksize

    rest = totalsize % chunksize

    if rest:
        yield chunks * chunksize, chunks * chunksize + rest
