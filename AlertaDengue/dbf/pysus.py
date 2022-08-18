import datetime
import glob
import logging
import time
import traceback as tb
from datetime import timedelta
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import psycopg2
from ad_main import settings
from psycopg2.extras import DictCursor
from pysus.online_data import SINAN

# get the start time
st = time.time()

logger = logging.getLogger(__name__)

db_config = {
    "database": settings.PSQL_DB,
    "user": settings.PSQL_USER,
    "password": settings.PSQL_PASSWORD,
    "host": settings.PSQL_HOST,
    "port": settings.PSQL_PORT,
}


def _get_postgres_connection():
    return psycopg2.connect(**db_config)


CID10 = {"dengue": "A90", "chikungunya": "A92.0", "zika": "A928"}

MAP_FIELDS = {
    "classi_fin": "CLASSI_FIN",
    "criterio": "CRITERIO",
    "cs_sexo": "CS_SEXO",
    "dt_notific": "DT_NOTIFIC",
    "dt_sin_pri": "DT_SIN_PRI",
    "cid10_codigo": "ID_AGRAVO",
    "municipio_geocodigo": "ID_MUNICIP",
    "ano_notif": "NU_ANO",
    "nu_idade_n": "NU_IDADE_N",
    "se_notif": "SEM_NOT",
    "se_sin_pri": "SEM_PRI",
    "resul_pcr": "RESUL_PCR_",
}

COL_TO_RENAME = dict(zip(MAP_FIELDS.values(), MAP_FIELDS.keys()))
COL_NAMES = list(MAP_FIELDS.values())


class Log:
    """
    Generate the log file with the traceback in the path.
    """

    file_path = "/tmp/pysus_data_error.log"
    fd = None

    @classmethod
    def start(cls):
        cls.fd = open(cls.file_path, "w")

    @classmethod
    def stop(cls):
        cls.fd.close()

    @classmethod
    def write(cls, message):
        cls.fd.write(message)
        cls.fd.write("\n")


@np.vectorize
def calc_birth_date(
    value: datetime.date,
    age: Union[np.int64, int],
    unit: Union[np.str_, str] = "Y",
) -> datetime.date:
    """
    Em tabelas do SINAN frequentemente a idade é representada
    como um inteiro que precisa ser parseado para retornar a idade
    em uma unidade cronológica padrão.
    :param unidade: idade: 'Y': anos, 'M' meses, 'D': dias, 'H': horas
    :param idade: inteiro ou sequencia de inteiros codificados.
    :return:
    """

    fator = {"Y": 1.0, "M": 12.0, "D": 365.0, "H": 365 * 24.0}
    if age >= 4000:  # idade em anos
        age_years = age - 4000
    elif age >= 3000 and age < 4000:  # idade em meses
        age_years = (age - 3000) / 12.0
    elif age >= 2000 and age < 3000:  # idade em dias
        age_years = (age - 2000) / 365.0
    elif age >= 1000 and age < 2000:  # idade em horas
        age_years = (age - 1000) / (365 * 24.0)
    else:
        age_years = np.nan
    age_dec = age_years * fator[unit]

    days_x_year = age_dec * 365

    if np.isnan(days_x_year):
        days_x_year = 1

    # entered_date = datetime.datetime.strptime(value, "%Y-%m-%d")

    birth_date = value - timedelta(days=int(days_x_year))

    return birth_date


def calculate_digit(dig):
    """
    Calcula o digito verificador do geocódigo de município.
    :param dig: geocódigo com 6 dígitos
    :return: dígito verificador
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
def add_dv(geocode: int) -> int:
    """
    Retorna o geocóodigo do município adicionando o digito verificador,
    se necessário.
    :param geocodigo: geocóodigo com 6 ou 7 dígitos
    """
    if len(str(geocode)) == 7:
        return int(geocode)
    elif len(str(geocode)) == 6:
        return int(str(geocode) + str(calculate_digit(geocode)))
    elif len(str(geocode)) == 0:
        return print(len(geocode))

    raise ValueError(f"geocode:{geocode} does not match!")


@np.vectorize
def check_geocode(geocode: str) -> Optional[int]:
    """
    Define None value if the field is empty or
    call add_dv function to add 7 digit to the geocode.
    """

    return None if geocode == "" else add_dv(geocode)


@np.vectorize
def fill_cid(disease: str) -> str:
    """
    Change CID10 for chikungunya disease.
    """

    return "A92.0" if disease == "A92." else str(disease)


@np.vectorize
def slice_se(epiweek: str) -> Optional[str]:
    """
    Slice the week from epiweek.
    """

    return None if epiweek == "" else str(epiweek)[-2:]


class PySUS(object):
    def __init__(self, year, disease):
        """ """

        self.FILE_NAME = Path(disease[:4].upper() + "BR" + year[-2:])
        self.PARQUET_DIR = Path(f"{self.FILE_NAME}.parquet")

        self.disease = disease
        self.year = year

    def get_data(self, year: int, disease: str) -> pd.DataFrame:
        """
        Get data from PySUS or fetch data
        from the parquet directory if it exists.
        param:
            year: str
            disease: str
        return pd.DataFrame
        """
        if not self.PARQUET_DIR.is_dir():
            print("Downloading data from the API")
            SINAN.download(int(year), disease, return_fname=True)

        fetch_pq_fname = glob.glob(f"{self.FILE_NAME}.parquet/*.parquet")

        chunks_list = [pd.read_parquet(f) for f in fetch_pq_fname]

        df = pd.concat(chunks_list, ignore_index=True)

        if "RESUL_PCR_" not in df.columns:
            print("...adding the result_pcr column to", self.FILE_NAME)
            df["RESUL_PCR_"] = 0

        return df[COL_NAMES].rename(columns=COL_TO_RENAME)

    def parse_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds the missing columns and parse the data.
        param: pd.DataFrame
        return: pd.DataFrame

        """
        df.reset_index(drop=True)
        df["nu_notific"] = df.index + 999999999
        df["municipio_geocodigo"] = check_geocode(df.municipio_geocodigo)
        df["cid10_codigo"] = fill_cid(df.cid10_codigo)
        df["dt_nasc"] = calc_birth_date(df.dt_notific, df.nu_idade_n, "Y")
        df["dt_digita"] = df.dt_notific
        df["se_notif"] = slice_se(df.se_notif)
        df["se_sin_pri"] = slice_se(df.se_sin_pri)
        df["criterio"] = (
            pd.to_numeric(df["criterio"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        df["classi_fin"] = (
            pd.to_numeric(df["classi_fin"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
        df["resul_pcr"] = (
            pd.to_numeric(df["resul_pcr"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

        return df

    def save(self):
        """
        Get database connection and insert PySUS data from dataframe.
        """
        Log.start()
        connection = _get_postgres_connection()

        join = lambda x: ", ".join(x)  # noqa F841

        logger.info("Connecting to PostgreSQL database")

        with connection.cursor(cursor_factory=DictCursor) as cursor:

            table_name = '"Municipio"."Notificacao"'
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            col_names = [c.name for c in cursor.description if c.name != "id"]

        insert_sql = (
            "INSERT INTO {}({}) VALUES ({}) on conflict "
            "on CONSTRAINT casos_unicos do UPDATE SET {}"
        ).format(
            table_name,
            ",".join(col_names),
            ",".join(["%s" for i in col_names]),
            ",".join(["{0}=excluded.{0}".format(j) for j in col_names]),
        )

        df_pysus = self.parse_dataframe(self.get_data(self.year, self.disease))

        print(df_pysus.se_notif.min(), "->", df_pysus.se_notif.max())

        for row in df_pysus[col_names].iterrows():
            with connection.cursor(cursor_factory=DictCursor) as cursor:

                i = row[0]
                row = row[1]

                try:
                    cursor.execute(insert_sql, row)
                except Exception:
                    Log.write(tb.format_exc() + "> " + row.to_json())

                if (i % 1000 == 0) and (i > 0):
                    logger.info(
                        f"{i} lines inserted."
                        "Committing changes to the database..."
                    )
                    connection.commit()

            connection.commit()

        logger.info(
            "Sinan {} rows in {} fields inserted in the database".format(
                df_pysus.shape[0], df_pysus.shape[1]
            )
        )

        Log.stop()
