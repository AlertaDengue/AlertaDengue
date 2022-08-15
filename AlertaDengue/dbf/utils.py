import glob
from pathlib import Path

import geopandas as gpd
import pandas as pd
from django.conf import settings
from simpledbf import Dbf5

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


def read_dbf(dbfname: str) -> pd.DataFrame:
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

    dbf = Dbf5(dbfname, codec="iso-8859-1")

    f_name = str(dbf.dbf)[:-4]

    all_expecet_fields = EXPECTED_FIELDS.copy()

    if f_name.startswith(("BR-DEN", "BR-CHIK")):
        all_expecet_fields.extend(["RESUL_PCR_", "CRITERIO", "CLASSI_FIN"])
    elif f_name.startswith(("BR-ZIKA")):
        all_expecet_fields.extend(["CRITERIO", "CLASSI_FIN"])
    else:
        all_expecet_fields

    pqt_to_dir = Path(DBFS_PQTDIR / f"{f_name}.parquet")

    if not pqt_to_dir.is_dir():
        print("Convert DBF to parquet...")
        Path.mkdir(pqt_to_dir, parents=True, exist_ok=True)
        for chunk, (lowerbound, upperbound) in enumerate(
            chunk_gen(1000, dbf.numrec)
        ):

            pq_fname = f"{pqt_to_dir}/{f_name}-{chunk}.parquet"

            df_gpd = gpd.read_file(
                dbfname,
                rows=slice(lowerbound, upperbound),
                ignore_geometry=True,
            )[all_expecet_fields]

            df_gpd = _parse_fields(df_gpd)

            df_gpd.to_parquet(pq_fname)

    fetch_pq_fname = glob.glob(f"{pqt_to_dir}/*.parquet")

    chunks_list = [
        pd.read_parquet(f, engine="fastparquet") for f in fetch_pq_fname
    ]

    return pd.concat(chunks_list, ignore_index=True)
