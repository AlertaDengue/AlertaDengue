import datetime
import glob
import logging
import time
import traceback as tb
from datetime import timedelta
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras as extras
from ad_main import settings
from dados.episem import episem
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

dtypes = {
    "dt_notific": "datetime64[ns]",
    "se_notif": "int",
    "ano_notif": "int",
    "dt_sin_pri": "datetime64[ns]",
    "se_sin_pri": "int",
    "dt_digita": "datetime64[ns]",
    "municipio_geocodigo": "int",
    "nu_notific": "int",
    "cid10_codigo": "string",
    "dt_nasc": "datetime64[ns]",
    "cs_sexo": "string",
    "nu_idade_n": "int",
    "resul_pcr": "int",
    "criterio": "int",
    "classi_fin": "int",
}


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
    In SINAN tables, age is often represented
    as an integer that needs to be parsed to return the age
    in a standard chronological unit.
    Parameters
    ----------
        unit: age: 'Y': years, 'M' months, 'D': days, 'H': hours.
        age: integer or sequence of encoded integers.
    Returns
    -------
        birth_date:  date of birth.
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


def calculate_digit(dig: int) -> int:
    """
    Calculates the check digit of the county geocode.
    Parameters
    ----------
        dig: geocode with 6 digit.
    Returns
    -------
        dv: geocode with 7 digit.
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
def add_dv(geocode: np.int64) -> int:
    """
    Returns the geocode of the municipality by adding the verifier digit.
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
def fill_cid(disease: np.str_) -> str:
    """
    Change CID10 for chikungunya disease.
    Parameters
    ----------
        disease: typo CID10 code
    Returns
    -------
        disease: disease fixed
    """

    return "A92.0" if disease == "A92." else str(disease)


@np.vectorize
def add_se(dt_notf: np.str_) -> int:
    """
    Adds the SE field if it is empty.
    Execute episem function to convert string date to epiweek.
    Parameters
    ----------
        dt_notf: yearweek.
    Returns
    -------
        week: last two digits of the epidemiological week.
    """
    epiweek = episem(str(dt_notf), sep="")

    return int(str(epiweek)[-2:])


@np.vectorize
def slice_se(epiweek: np.str_, dt_notf: np.datetime64()):
    """
    Get the epiweek from position -2.
    Removes the invalid character from the epidemiological week.
    """
    not_valid_char = ["-", ""]

    return (
        add_se(dt_notf)
        if any(x in epiweek for x in not_valid_char)
        else int(str(epiweek)[-2:])
    )


class PySUS(object):
    def __init__(self, year, disease):
        self.FILE_NAME = Path(disease[:4].upper() + "BR" + year[-2:])
        self.PARQUET_DIR = Path(f"{self.FILE_NAME}.parquet")

        self.disease = disease
        self.year = year

    def get_data(self, year: int, disease: str) -> pd.DataFrame:
        """
        Get data from PySUS or fetch data
        from the parquet directory if it exists.
        Parameters
        ----------
            year: available year.
            disease: disease name.
        Returns
        -------
            df: dataframe with expected fields and renamed columns.
        """
        if not self.PARQUET_DIR.is_dir():
            logger.info("Downloading data from the API...")
            SINAN.download(int(year), disease, return_fname=True)

        logger.info("Reading and concatenating parquet files...")
        for i, f in enumerate(
            glob.glob(f"{self.FILE_NAME}.parquet/*.parquet")
        ):
            print(i, f)
            if i == 0:
                df = pd.read_parquet(f)
            else:
                df = pd.concat([df, pd.read_parquet(f)], ignore_index=True)

        if "RESUL_PCR_" not in df.columns:
            logger.info(f"...adding the result_pcr column to {self.FILE_NAME}")
            df["RESUL_PCR_"] = 0

        return df[COL_NAMES].rename(columns=COL_TO_RENAME)

    def parse_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds the missing columns and parse the data.
        Parameters
        ----------
          df: dataframe with expected columns.
        Returns
        -------
          df: dataframe with data parse.
        """
        logger.info("Parsing the dataframe...")

        df = df[df["municipio_geocodigo"].map(len) > 5].copy()
        df.reset_index(drop=True)
        df["nu_notific"] = df.index + 999999999
        df["municipio_geocodigo"] = add_dv(df.municipio_geocodigo)
        df["cid10_codigo"] = fill_cid(df.cid10_codigo)
        df["dt_nasc"] = calc_birth_date(df.dt_notific, df.nu_idade_n, "Y")
        df["dt_digita"] = df.dt_notific
        df["se_notif"] = slice_se(df.se_notif, df.dt_notific)
        df["se_sin_pri"] = slice_se(df.se_sin_pri, df.dt_notific)
        df["criterio"] = pd.to_numeric(df["criterio"], errors="coerce").fillna(
            0
        )
        df["classi_fin"] = pd.to_numeric(
            df["classi_fin"], errors="coerce"
        ).fillna(0)
        df["resul_pcr"] = pd.to_numeric(
            df["resul_pcr"], errors="coerce"
        ).fillna(0)

        return df.astype(dtypes, errors="ignore")

    def save_to_pgsql(self):
        """
        Get database connection and insert PySUS data from dataframe.
        Only inserts data, does not update existing rows.
        """
        connection = _get_postgres_connection()

        logger.info("Connecting to PostgreSQL database")

        with connection.cursor(cursor_factory=DictCursor) as cursor:
            table_name = '"Municipio"."Notificacao"'
            df = self.parse_dataframe(self.get_data(self.year, self.disease))
            tuples = [tuple(x) for x in df.to_numpy()]
            cols = ",".join(list(df.columns))
            logger.info("Inserting data...")
            insert_sql = "INSERT INTO %s(%s) VALUES %%s" % (table_name, cols)
            try:
                extras.execute_values(cursor, insert_sql, tuples)
                connection.commit()
            except Exception:
                print(tb.format_exc())
                connection.rollback()
                cursor.close()
                return 1
            cursor.close()
            logger.info(
                "Sinan {} rows in {} fields inserted in the database".format(
                    df.shape[0], df.shape[1]
                )
            )

    def upsert_to_pgsql(self):
        """
        Get database connection and insert PySUS data from dataframe.
        Inserts or updates the row if it already exists.
        """
        Log.start()
        connection = _get_postgres_connection()

        df_pysus = self.parse_dataframe(self.get_data(self.year, self.disease))

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
