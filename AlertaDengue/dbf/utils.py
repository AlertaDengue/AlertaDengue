import glob
import os

import geopandas as gpd
import pandas as pd
from simpledbf import Dbf5

DBFS_PQTDIR = '/MEDIA_ROOT/dbfs_parquet'

expected_fields = [
    u'NU_ANO',
    u'ID_MUNICIP',
    u'ID_AGRAVO',
    u'DT_SIN_PRI',
    u'SEM_PRI',
    u'DT_NOTIFIC',
    u'NU_NOTIFIC',
    u'SEM_NOT',
    u'DT_DIGITA',
    u'DT_NASC',
    u'NU_IDADE_N',
    u'CS_SEXO',
    # u'RESUL_PCR',
    u'CRITERIO',
    u'CLASSI_FIN',
]

synonyms = {u'ID_MUNICIP': [u'ID_MN_RESI']}

expected_date_fields = [u'DT_SIN_PRI', u'DT_NOTIFIC', u'DT_DIGITA', u'DT_NASC']

FIELD_MAP = {
    'dt_notific': "DT_NOTIFIC",
    'se_notif': "SEM_NOT",
    'ano_notif': "NU_ANO",
    'dt_sin_pri': "DT_SIN_PRI",
    'se_sin_pri': "SEM_PRI",
    'dt_digita': "DT_DIGITA",
    'bairro_nome': "NM_BAIRRO",
    'bairro_bairro_id': "ID_BAIRRO",
    'municipio_geocodigo': "ID_MUNICIP",
    'nu_notific': "NU_NOTIFIC",
    'cid10_codigo': "ID_AGRAVO",
    'cs_sexo': "CS_SEXO",
    'dt_nasc': "DT_NASC",
    'nu_idade_n': "NU_IDADE_N",
    'resul_pcr': "RESUL_PCR",
    'criterio': "CRITERIO",
    'classi_fin': "CLASSI_FIN",
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
        df = df.dropna(subset=['ID_MUNICIP'])
    elif "ID_MN_RESI" in df.columns:
        df = df.dropna(subset=['ID_MN_RESI'])
        df["ID_MUNICIP"] = df.ID_MN_RESI
        del df['ID_MN_RESI']

    for col in filter(lambda x: x.startswith("DT"), df.columns):
        try:
            df[col] = pd.to_datetime(df[col])  # , errors='coerce')
        except ValueError:
            df[col] = pd.to_datetime(df[col], errors='coerce')

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
    fname_topath = str(dbf.dbf)[:-4]
    for chunk, (lowerbound, upperbound) in enumerate(
        chunk_gen(1000, dbf.numrec)
    ):
        pq_fname = os.path.join(
            f'{DBFS_PQTDIR}', f'{fname_topath}-{chunk}.parquet'
        )
        df_gpd = gpd.read_file(
            dbfname, rows=slice(lowerbound, upperbound), ignore_geometry=True,
        )
        df_gpd = _parse_fields(df_gpd)
        df_gpd[expected_fields].to_parquet(pq_fname)

    fetch_pq_fname = os.path.join(f'{DBFS_PQTDIR}', f'{fname_topath}')
    return glob.glob(f'{fetch_pq_fname}*.parquet')
