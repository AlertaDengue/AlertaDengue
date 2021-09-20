import glob
import os

# from typing import Callable

import geopandas as gpd
from simpledbf import Dbf5


DBFS_PQDIR = '/tmp/dbfs_parquet'

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
}


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
        df = gpd.read_file(
            dbfname, rows=slice(lowerbound, upperbound), ignore_geometry=True,
        )

        pq_fname = os.path.join(
            f'{DBFS_PQDIR}', f'{fname_topath}-{chunk}.parquet'
        )

        df[FIELD_MAP.values()].to_parquet(pq_fname)

    fetch_pq_fname = os.path.join(f'{DBFS_PQDIR}', f'{fname_topath}')
    return glob.glob(f'{fetch_pq_fname}*.parquet')
