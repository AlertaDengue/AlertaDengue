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

REQUIRED_DATE_FIELDS = ["DT_SIN_PRI", "DT_NOTIFIC", "DT_DIGITA", "DT_NASC"]

REQUIRED_FIELDS = REQUIRED_DATE_FIELDS  # +

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
                f"(Condition SEM_NOT) for {filename}."
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

    df["CS_SEXO"] = np.where(
        df["CS_SEXO"].isin(["M", "F"]), df["CS_SEXO"], "I"
    ).astype(str)

    valid_rows: list[pd.Series] = []
    misparsed_rows: list[pd.Series] | list = []

    for _, row in df.iterrows():
        try:
            valid_rows.append(sinan_parse_row(row, sinan_obj))
        except:
            misparsed_rows.append(row)

    df = pd.DataFrame(valid_rows, columns=df.columns)
    df = df.reset_index(drop=True)

    misparsed_df = pd.DataFrame(misparsed_rows, columns=df.columns)

    if not misparsed_df.empty:
        sinan_obj.parse_error = True
        sinan_obj.save()

        logger.warning(
            f"Parsing residues found for {sinan_obj.filename}, please check "
            f"{str(sinan_obj.misparsed_file)} manually."
        )

        misparsed_df.to_csv(
            str(sinan_obj.misparsed_file),
            index=False,
            mode="a",
        )

    return df


def sinan_parse_row(row: pd.Series, sinan_obj) -> pd.Series:
    for col in REQUIRED_DATE_FIELDS:
        row[col] = pd.to_datetime(row[col])

    nu_notific = row["NU_NOTIFIC"]
    char_to_replace = {",": "", "'": "", ".": ""}
    if str(nu_notific).isdigit():
        row["NU_NOTIFIC"] = int(row["NU_NOTIFIC"])
    elif (
        "".join(
            [str(c) for c in str(nu_notific) if c not in char_to_replace]
        ).isdigit()
    ):
        row["NU_NOTIFIC"] = int("".join(
            [str(c) for c in str(nu_notific) if c not in char_to_replace]
        ))
    else:
        row["NU_NOTIFIC"] = None
    row["ID_MUNICIP"] = list(map(add_dv, row["ID_MUNICIP"]))

    for col in ["RESUL_PCR_", "CRITERIO", "CLASSI_FIN"]:
        try:
            row[col] = pd.to_numeric(row[col])
        except ValueError:
            row[col] = 0

    if row["ID_AGRAVO"] not in list(DISEASE_CID.values()):
        row["ID_AGRAVO"] = DISEASE_CID[sinan_obj.disease]

    if row["SEM_PRI"] != None:
        row["SEM_PRI"] = str(row["SEM_PRI"])[-2:]

    if row["NU_ANO"] in [None, np.nan, "", 0]:
        row["NU_ANO"] = sinan_obj.notification_year
    else:
        row["NU_ANO"] = int(row["NU_ANO"])

    row["SEM_NOT"] = int(str(int(row["SEM_NOT"]))[-2:])

    return row


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

    if "." in str(geocode):
        geocode = str(int(float(geocode)))

    if len(str(geocode)) == 7:
        return int(geocode)
    elif len(str(geocode)) == 6:
        return int(str(geocode) + str(calculate_digit(geocode)))

    raise ValueError(_(f"geocode:{geocode} does not match!"))


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
