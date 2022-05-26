import glob
from pathlib import Path

import geopandas as gpd
import pandas as pd
from django.conf import settings
from simpledbf import Dbf5

DBFS_PQTDIR = Path(settings.TEMP_FILES_DIR) / "dbfs_parquet"


expected_fields = [
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
    # "RESUL_PCR_",
    # "CRITERIO",
    # "CLASSI_FIN",
]

synonyms = {"ID_MUNICIP": ["ID_MN_RESI"]}

expected_date_fields = ["DT_SIN_PRI", "DT_NOTIFIC", "DT_DIGITA", "DT_NASC"]

FIELD_MAP = {
    "dt_notific": "DT_NOTIFIC",
    "se_notif": "SEM_NOT",
    "ano_notif": "NU_ANO",
    "dt_sin_pri": "DT_SIN_PRI",
    "se_sin_pri": "SEM_PRI",
    "dt_digita": "DT_DIGITA",
    "bairro_nome": "NM_BAIRRO",
    "bairro_bairro_id": "ID_BAIRRO",
    "municipio_geocodigo": "ID_MUNICIP",
    "nu_notific": "NU_NOTIFIC",
    "cid10_codigo": "ID_AGRAVO",
    "cs_sexo": "CS_SEXO",
    "dt_nasc": "DT_NASC",
    "nu_idade_n": "NU_IDADE_N",
    "resul_pcr": "RESUL_PCR_",
    "criterio": "CRITERIO",
    "classi_fin": "CLASSI_FIN",
}


def _parse_fields(df: gpd) -> pd:
    """
    Rename columns and set type datetime when startswith "DT"
    Parameters
    ----------
    geopandas
    Returns
    -------
    dataframe
    """

    df = df.copy(deep=True)

    if "ID_MUNICIP" in df.columns:
        df = df.dropna(subset=["ID_MUNICIP"])
    elif "ID_MN_RESI" in df.columns:
        df = df.dropna(subset=["ID_MN_RESI"])
        df["ID_MUNICIP"] = df.ID_MN_RESI
        del df["ID_MN_RESI"]

    for col in filter(lambda x: x.startswith("DT"), df.columns):
        try:
            df[col] = pd.to_datetime(df[col])  # , errors='coerce')
        except ValueError:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def chunk_gen(chunksize, totalsize):
    """
    Create chunks
    Parameters
    ----------
    chunksize: int
    totalsize: int
    Returns
    -------
    yield: += chunks * chunksize
    """
    chunks = totalsize // chunksize

    for i in range(chunks):
        yield i * chunksize, (i + 1) * chunksize

    rest = totalsize % chunksize

    if rest:
        yield (chunks * chunksize, (chunks * chunksize) + rest)


def chunk_dbf_toparquet(dbfname) -> glob:
    """
    name: Generator to read the dbf in chunks
    Filtering columns from the field_map dictionary on dataframe and export
    to parquet files
    Parameters
    ----------
    dbf_fname: str
        path: path to dbf file
    Returns
    -------
    files:
        .parquet list
    """

    dbf = Dbf5(dbfname)

    f_name = str(dbf.dbf)[:-4]

    if f_name.startswith("BR-DEN"):
        expected_fields.extend(["RESUL_PCR_", "CRITERIO", "CLASSI_FIN"])

    for chunk, (lowerbound, upperbound) in enumerate(
        chunk_gen(1000, dbf.numrec)
    ):
        pq_fname = DBFS_PQTDIR / f"{f_name}-{chunk}.parquet"

        df_gpd = gpd.read_file(
            dbfname,
            rows=slice(lowerbound, upperbound),
            ignore_geometry=True,
        )
        df_gpd = _parse_fields(df_gpd)

        df_gpd[expected_fields].to_parquet(pq_fname)

    fetch_pq_fname = DBFS_PQTDIR / f_name

    return glob.glob(f"{fetch_pq_fname}*.parquet")
