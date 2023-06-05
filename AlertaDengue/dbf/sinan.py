import logging
from typing import Any, List, Optional, Tuple

import psycopg2
from dbf.utils import (  # NOQA E501
    FIELD_MAP,
    drop_duplicates_from_dataframe,
    parse_data,
    read_dbf,
)
from django.conf import settings
from psycopg2.extras import DictCursor

logger = logging.getLogger(__name__)


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

        return data_inicio, data_fim  # type: ignore

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
        self.default_cid = default_cid

        logger.info("Establishing connection to PostgreSQL database...")
        connection = self._get_postgres_connection()

        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            col_names = [c.name for c in cursor.description if c.name != "id"]
            self._fill_missing_columns(col_names)
            valid_col_names = [FIELD_MAP[n] for n in col_names]

            # Insert Query data
            insert_sql = (
                f"INSERT INTO {table_name}({','.join(col_names)}) "
                f"VALUES ({','.join(['%s' for _ in col_names])}) "
                f"ON CONFLICT ON CONSTRAINT casos_unicos DO UPDATE SET "
                f"{','.join([f'{j}=excluded.{j}' for j in col_names])}"
            )

            logger.info("Parsing rows and converting data types...")

            df = parse_data(
                self.tabela[valid_col_names],
                default_cid,  # type: ignore
                self.ano,
            )

            # Remove duplicate rows
            df = drop_duplicates_from_dataframe(
                df, default_cid, self.ano  # type: ignore
            )

            logger.info(
                f"Starting iteration to upsert data into {table_name}..."
            )

            try:
                # Execute the INSERT statement
                rows = [tuple(row) for row in df.itertuples(index=False)]
                cursor.executemany(insert_sql, rows)
                connection.commit()
            except psycopg2.errors.StringDataRightTruncation as e:
                # Handle the error accordingly (e.g., modify the field length,
                # truncate the value, etc.)
                error_message = str(e)
                field_start_index = error_message.find('"') + 1
                field_end_index = error_message.find('"', field_start_index)
                logger.error(
                    f"""Field causing the error: {
                        error_message[field_start_index:field_end_index]
                    }"""
                )

            logger.info(
                "Inserted {} rows with {} fields into the '{}' table.".format(
                    df.shape[0], df.shape[1], table_name
                )
            )
