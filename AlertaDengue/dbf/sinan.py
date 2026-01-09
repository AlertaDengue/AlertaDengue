from typing import Any, List, Optional

import pandas as pd
import psycopg2
from dbf.utils import (
    FIELD_MAP,
    drop_duplicates_from_dataframe,
    parse_data,
    read_dbf,
)
from django.conf import settings
from loguru import logger
from psycopg2.extras import DictCursor


class Sinan(object):
    """
    Introspects a SINAN DBF file, perform data cleaning and type conversion,
    and prepare the data for insertion into another database.
    """

    def __init__(
        self, dbf_fname: str, year: int, encoding: str = "iso=8859-1"
    ) -> None:
        """
        Instantiates a SINAN object by loading data from the specified file.
        :param dbf_fname: The name of the Sinan dbf file (str)
        :param year: The year of the data (int)
        :param encoding: The file encoding (str)
        :return: None
        """

        logger.info("Establishing connection to PostgreSQL database...")
        self.db_engine = settings.DB_ENGINE

        logger.info("Formatting fields and reading chunks from parquet files")

        self.table = read_dbf(dbf_fname)
        self.year = year
        self.dbf_fname = dbf_fname

    def _fill_missing_columns(self, col_names: List[str]) -> None:
        """
        Check if the table to be inserted contains all columns
        required in the database model.
        If not, create these columns filled with Null values to allow
        for database insertion.
        Parameters
        ----------
        col_names : List[str]
            A list of column names to check.
        Returns
        -------
        None
        """
        for nm in col_names:
            if FIELD_MAP[nm] not in self.table.columns:
                self.table[FIELD_MAP[nm]] = None

    def save_to_pgsql(
        self,
        table_name: str = '"Municipio"."Notificacao"',
        default_cid: Optional[Any] = None,
    ) -> None:
        """
        Save data to PostgreSQL table.

        Parameters
        ----------
        table_name : str, optional
            The name of the table to save data to,
            by default '"Municipio"."Notificacao"'
        default_cid : Any, optional
            The default value for the 'cid' column, by default None

        Returns
        -------
        None
        """

        # Set the default_cid attribute
        self.default_cid = default_cid

        # Log the start of the transaction process
        logger.info(
            f"Starting the SINAN transaction process for the {self.year} year "
            f"using the {self.dbf_fname} file."
        )

        # Start a transaction and create a cursor
        with self.db_engine.begin() as conn:
            cursor = conn.connection.cursor(cursor_factory=DictCursor)

            # Execute a query to get the column names of the table
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            col_names = [c.name for c in cursor.description if c.name != "id"]

            # Fill missing columns in the table
            self._fill_missing_columns(col_names)

            # Create a list of valid column names based on FIELD_MAP
            valid_col_names = [FIELD_MAP[n] for n in col_names]

            # Create the insert query
            insert_sql = (
                f"INSERT INTO {table_name}({','.join(col_names)}) "
                f"VALUES ({','.join(['%s' for _ in col_names])}) "
                f"ON CONFLICT ON CONSTRAINT casos_unicos DO UPDATE SET "
                f"{','.join([f'{j}=excluded.{j}' for j in col_names])}"
            )

            try:
                # Parse the data using the parse_data function
                df_parsed = parse_data(
                    self.table[valid_col_names],
                    default_cid,
                    self.year,
                )

                # Remove duplicate rows from the parsed data
                df_without_duplicates = drop_duplicates_from_dataframe(
                    df_parsed, default_cid, self.year
                )

                df_without_duplicates = df_without_duplicates.replace(
                    {pd.NA: None}
                )

                # Log the start of the upsert iteration
                logger.info(
                    f"Starting iteration to upsert data into {table_name}..."
                )

                # Execute the insert statement for each row in the dataframe
                rows = [
                    tuple(row)
                    for row in df_without_duplicates.itertuples(index=False)
                ]
                cursor.executemany(insert_sql, rows)

                # Commit the transaction
                conn.connection.commit()

            except psycopg2.errors.StringDataRightTruncation as e:
                # Handle the error caused by string data right truncation
                error_message = str(e)
                field_start_index = error_message.find('"') + 1
                field_end_index = error_message.find('"', field_start_index)
                logger.error(
                    f"""Field causing the error: {
                        error_message[field_start_index:field_end_index]
                    }"""
                )

            # Log the number of rows and fields inserted
            logger.info(
                f"Inserted {df_without_duplicates.shape[0]} rows with "
                f"{df_without_duplicates.shape[1]} fields into "
                f"{table_name} table."
            )
