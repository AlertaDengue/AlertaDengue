import glob
import logging
from pathlib import Path
from typing import List

import dask.dataframe as dd
import geopandas as gpd
import pandas as pd

# from dask.distributed import Client
from django.conf import settings
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
            df.to_parquet(parquet_fname)

    fetch_pq_fname = glob.glob(f"{parquet_dir}/*.parquet")
    chunks_list = [
        dd.read_parquet(f, engine="fastparquet") for f in fetch_pq_fname
    ]

    logger.info("Concatenating the chunks...")
    return dd.concat(chunks_list, ignore_index=True).compute()
