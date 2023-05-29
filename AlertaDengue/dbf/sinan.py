import logging
from typing import Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import psycopg2

# from dbfread import DBF
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from psycopg2.extras import DictCursor, execute_values

from .utils import FIELD_MAP, read_dbf

logger = logging.getLogger(__name__)


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
    elif len(str(geocode)) == 0:
        return logger.info(len(geocode))

    raise ValueError(f"geocode:{geocode} does not match!")


@np.vectorize
def fix_nu_notif(value: str) -> int:
    """
    Formats NU_NOTIF field value.
    Parameters
    ----------
        value (str): Value of NU_NOTIF field.
    Returns
    -------
        int: Formatted NU_NOTIF field value.
    Raises:
    -------
        ValueError: If value cannot be converted to int.
    """

    char_to_replace = {",": "", "'": "", ".": ""}

    try:
        value = None if pd.isnull(value) else int(value)
    except ValueError as e:
        if any(x in value for x in list(char_to_replace)):
            # Replace multiple characters.
            value = value.translate(str.maketrans(char_to_replace))
        else:
            logger.error(e)

    return value


@np.vectorize
def convert_data_types(col: any, dtype: type) -> any:
    """
    Converts column data types to the specified type.
    Parameters
    ----------
        col (any): The column to convert.
        dtype (type): The data type to convert the column to.
    Returns
    -------
        any: The converted column.
    """

    if pd.isnull(col):
        return None
    elif dtype == str:
        return str(col)
    elif dtype == int:
        return int(col or 0)
    else:
        return dtype.type(col)


@np.vectorize
def fill_id_agravo(col: np.ndarray, default_cid: str) -> np.ndarray:
    """
    Fills missing values in col with default_cid.
    Parameters
    ----------
        col (np.ndarray): A numpy array with missing values.
        default_cid (str): A default value to fill in the missing values.
    Returns
    -------
        np.ndarray: A numpy array with missing values filled using default_cid.
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
def convert_date(col: Union[pd.Series, np.ndarray]) -> np.ndarray:
    """
    Convert a column of dates to datetime.date objects.

    Parameters
    ----------
    col : Union[pd.Series, np.ndarray]
        A pandas.Series or numpy.ndarray containing date strings.

    Returns
    -------
    np.ndarray
        A numpy.ndarray of datetime.date objects.
    """

    if pd.isnull(col):
        return None
    else:
        return pd.Timestamp(col).to_pydatetime().date()


@np.vectorize
def convert_sem_not(col: np.ndarray) -> np.ndarray:
    """
    Converts a given column of integers to its last two digits.
    Parameters
    ----------
        col (numpy.ndarray): A column of integers to be converted.
    Returns
    -------
        numpy.ndarray: A column of integers with only its last two digits.
    """

    return int(str(int(col))[-2:])


@np.vectorize
def convert_nu_ano(ano: str, col: pd.Series) -> np.ndarray:
    """
    Convert the given 'ano' string to an integer if 'col' is NaN,
    otherwise convert 'col' to an integer.
    Parameters
    ----------
        ano: A string representing the year.
        col: A pandas series representing a column of a dataframe.
    Returns
    -------
        A numpy array of integers.
    """

    return int(ano) if pd.isnull(col) else int(col)


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

    if not col:
        return None
    else:
        return int(str(col)[-2:])


def parse_data(df: pd.DataFrame, default_cid: str, ano: int) -> pd.DataFrame:
    """
    Parse and convert data types for COVID-19 notification data.
    Parameters
    ----------
        df (pandas.core.frame.DataFrame): The dataframe to parse.
        default_cid (str): The default CID code.
        ano (int): The year of the notification data.
    Returns
    -------
        pandas.core.frame.DataFrame: The parsed dataframe.
    """

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

    df["NU_ANO"] = convert_nu_ano(ano, df.NU_ANO)

    df["SEM_NOT"] = convert_sem_not(df.SEM_NOT)

    return df


class Sinan(object):
    """
    Introspects a SINAN DBF file, perform data cleaning and type conversion,
    and prepare the data for insertion into another database.
    """

    db_config = {
        "database": settings.PSQL_DB,
        "user": settings.PSQL_USER,
        "password": settings.PSQL_PASSWORD,
        "host": settings.PSQL_HOST,
        "port": settings.PSQL_PORT,
    }

    def __init__(
        self, dbf_fname: str, ano: int, encoding: str = "iso=8859-1"
    ) -> None:
        """
        Instantiates a SINAN object by loading data from the specified file.
        :param dbf_fname: The name of the Sinan dbf file (str)
        :param ano: The year of the data (int)
        :param encoding: The file encoding (str)
        :return: None
        """
        logger.info("Formatting fields and reading chunks from parquet files")

        self.tabela = read_dbf(dbf_fname)
        self.ano = ano

        logger.info(
            f"""Starting the SINAN instantiation process for the {ano} year
            using the {dbf_fname} file.
            """
        )

    @property
    def time_span(self) -> Tuple[str, str]:
        """
        Returns the temporal scope of the database as
            a tuple of start and end dates.
        Returns
        -------
            A tuple containing start and end dates in string format
              (data_inicio, data_fim).
        """

        data_inicio = self.tabela["DT_NOTIFIC"].min()
        data_fim = self.tabela["DT_NOTIFIC"].max()

        return data_inicio, data_fim

    def _fill_missing_columns(self, col_names: List[str]) -> None:
        """
        Check if the table to be inserted contains all columns
            required in the database model.
        If not, create these columns filled with Null values to allow
            for database insertion.
        Parameters
        ----------
        col_names : numpy.ndarray
            A numpy array of column names to check.
        Returns
        -------
        None
        """

        for nm in col_names:
            if FIELD_MAP[nm] not in self.tabela.columns:
                self.tabela[FIELD_MAP[nm]] = None

    def _get_postgres_connection(self) -> Any:
        """
        Returns a connection to a Postgres database.
        Parameters
        ----------
            self (object): The instance of the class calling this method.
        Returns
        -------
            Any: A connection to the Postgres database.
        """

        return psycopg2.connect(**self.db_config)

    def save_to_pgsql(
        self,
        table_name: str = '"Municipio"."Notificacao"',
        default_cid: Optional[Any] = None,
    ) -> None:
        """
        Save data to PostgreSQL table.
        Parameters
        ----------
            self (object): The class object.
            table_name (str): The name of the table to save data to
                Defaults to '"Municipio"."Notificacao"'.
            default_cid (Any, optional): The default value
                for the 'cid' column. Defaults to None.
        Returns
        -------
            None
        """

        logger.info("Establishing connection to PostgreSQL database...")
        connection = self._get_postgres_connection()

        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            col_names = [c.name for c in cursor.description if c.name != "id"]
            self._fill_missing_columns(col_names)
            valid_col_names = [FIELD_MAP[n] for n in col_names]

            insert_sql = (
                "INSERT INTO {}({}) VALUES %s on conflict "
                "on CONSTRAINT casos_unicos do UPDATE SET {}"
            ).format(
                table_name,
                ",".join(col_names),
                ",".join(["{0}=excluded.{0}".format(j) for j in col_names]),
            )

            logger.info("Parsing rows and converting data types...")
            df = parse_data(
                self.tabela[valid_col_names], default_cid, self.ano
            )

            logger.info(
                f"Starting iteration to upsert data into {table_name}..."
            )

            try:
                # Execute the INSERT statement
                rows = [tuple(row) for row in df.itertuples(index=False)]
                execute_values(cursor, insert_sql, rows, page_size=1000)
                connection.commit()
            except psycopg2.errors.StringDataRightTruncation as e:
                # Extract the field causing the error from the error message
                error_message = str(e)
                field_start_index = error_message.find('"') + 1
                field_end_index = error_message.find('"', field_start_index)
                logger.error(
                    f"""Field causing the error: {
                        error_message[field_start_index:field_end_index]
                    }"""
                )
                # Handle the error accordingly (e.g., modify the field length,
                # truncate the value, etc.)

            logger.info(
                "Inserted {} rows with {} fields into the '{}' table.".format(
                    self.tabela.shape[0], self.tabela.shape[1], table_name
                )
            )
