import os
import csv
from pathlib import Path
from django.core.mail import send_mail

import psycopg2
import pandas as pd
import geopandas as gpd
import dask.dataframe as dd
from loguru import logger
from simpledbf import Dbf5
from celery import shared_task
from celery.result import AsyncResult
from psycopg2.extras import DictCursor

from django.utils.translation import gettext_lazy as _
from django.conf import settings

from ad_main.settings import get_sqla_conn
from .models import SINAN, Status
from .sinan.utils import (
    sinan_drop_duplicates_from_dataframe,
    sinan_parse_fields,
    chunk_gen
)

DB_ENGINE = get_sqla_conn(database="dengue")


@shared_task
def process_sinan_file(sinan_pk: str) -> bool:
    sinan = SINAN.objects.get(pk=sinan_pk)

    sinan.status = Status.CHUNKING
    sinan.save()

    fpath = Path(sinan.filepath)

    try:
        if fpath.suffix == ".csv":
            sniffer = csv.Sniffer()

            with open(fpath, "r") as f:
                data = f.read(10240)
                sep = sniffer.sniff(data).delimiter

            result: AsyncResult = chunk_csv_file.delay(  # pyright: ignore
                str(fpath), sep=sep
            )

        elif fpath.suffix == ".dbf":
            result: AsyncResult = chunk_dbf_file.delay(  # pyright: ignore
                str(fpath)
            )

        else:
            err = f"Unknown file type {fpath.suffix}"
            logger.error(err)
            sinan.status = Status.ERROR
            sinan.status_error = err
            sinan.save()
            return False

    except Exception as e:
        sinan.status = Status.ERROR
        sinan.status_error = f"Error chunking file: {e}"
        sinan.save()
        return False

    chunks = result.get(follow_parents=True)

    if chunks:
        logger.debug(f"Parsed {len(chunks)} chunks for {sinan.filename}")
        inserted: AsyncResult = (
            parse_insert_chunks_on_database
            .delay(sinan_pk)  # pyright: ignore
        )

        if not inserted.get(follow_parents=True):
            return False
        return True

    logger.error(f"No chunks parsed for {sinan.filename}")
    sinan.status = Status.ERROR
    sinan.status_error = f"No chunks were parsed"
    sinan.save()
    return False


@shared_task
def chunk_csv_file(file_path: str, sep: str) -> list[str]:
    ...


@shared_task
def chunk_dbf_file(file_path: str, chunks_dir: str) -> None:
    logger.info("Converting DBF file to Parquet chunks")

    dbf = Dbf5(file_path, codec="iso-8859-1")
    dbf_name = str(dbf.dbf)[:-4]

    if not os.path.exists(chunks_dir):
        os.mkdir(chunks_dir)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} does not exist")

    for chunk, (lowerbound, upperbound) in enumerate(
        chunk_gen(1000, dbf.numrec)
    ):
        parquet_fname = os.path.join(chunks_dir, f"{dbf_name}-{chunk}.parquet")
        df = gpd.read_file(
            file_path,
            rows=slice(lowerbound, upperbound),
            ignore_geometry=True,
            engine="fastparquet"
        )
        df.to_parquet(parquet_fname)
        logger.info(f"Chunk {parquet_fname} parsed for {dbf_name}")


@shared_task
def parse_insert_chunks_on_database(sinan_pk: str) -> bool:
    sinan = SINAN.objects.get(pk=sinan_pk)

    misparsed_csv_file = (
        Path(str(settings.DBF_SINAN)) / "residue_csvs" /
        f"RESIDUE_{Path(sinan.filename).with_suffix('.csv')}"
    )

    misparsed_csv_file.touch()

    sinan.misparsed_file = str(misparsed_csv_file.absolute())
    sinan.status = Status.INSERTING
    sinan.save()

    chunks_list = [chunk for chunk in Path(sinan.chunks_dir).glob("*.parquet")]

    uploaded: bool = False
    with DB_ENGINE.begin() as conn:  # pyright: ignore
        for chunk in chunks_list:
            try:
                df: dd = dd.read_parquet(  # pyright: ignore
                    str(chunk.absolute()),
                    engine="fastparquet"
                )
            except Exception as e:
                err = f"Error reading chunks for {sinan.filename}: {e}"
                logger.error(err)
                misparsed_csv_file.unlink(missing_ok=True)
                sinan.status = Status.ERROR
                sinan.misparsed_file = None
                sinan.status_error = err
                sinan.save()
                return False

            try:
                df = sinan_drop_duplicates_from_dataframe(
                    df,  # pyright: ignore
                    sinan.filename
                )
            except Exception as e:
                err = f"Error dropping duplicates from {sinan.filename}: {e}"
                logger.error(err)
                sinan.status = Status.ERROR
                sinan.misparsed_file = None
                sinan.status_error = err
                sinan.save()
                return False

            # Can't throw any exception
            df = sinan_parse_fields(
                df,  # pyright: ignore
                sinan
            )

            uploaded = save_to_pgsql(
                df,  # pyright: ignore
                sinan,
                conn
            )

        if uploaded:
            conn.connection.commit()

            if sinan.parse_error:
                sinan.status = Status.FINISHED_MISPARSED
                # send_mail() # TODO: send mail with link to misparsed csv file
                return True
            else:
                sinan.status = Status.FINISHED
                misparsed_csv_file.unlink(missing_ok=True)
                sinan.misparsed_file = None
                sinan.save()
                # send_mail(): # TODO: send successful insert email
                return True
        else:
            # send_mail(): # TODO: send failed insert email
            return False


def save_to_pgsql(
    df: pd.DataFrame, sinan_obj: SINAN, conn
) -> bool:
    # Log the start of the transaction process
    logger.info(
        f"Starting the SINAN transaction process for {sinan_obj.filename}"
    )

    # Start a transaction and create a cursor
    try:
        cursor = conn.connection.cursor(cursor_factory=DictCursor)

        # Execute a query to get the column names of the table
        cursor.execute(
            f"SELECT * FROM {sinan_obj.table_schema} LIMIT 1;"
        )
        col_names = [c.name for c in cursor.description if c.name != "id"]

        # Create the insert query
        insert_sql = (
            f"INSERT INTO {sinan_obj.table_schema}({','.join(col_names)}) "
            f"VALUES ({','.join(['%s' for _ in col_names])}) "
            f"ON CONFLICT ON CONSTRAINT casos_unicos DO UPDATE SET "
            f"{','.join([f'{j}=excluded.{j}' for j in col_names])}"
        )

        # Execute the insert statement for each row in the dataframe
        rows = [
            tuple(row)
            for row in df.itertuples(index=False)
        ]
        cursor.executemany(insert_sql, rows)

    except Exception as e:
        error_message = str(e)
        field_start_index = error_message.find('"') + 1
        field_end_index = error_message.find('"', field_start_index)
        err = (
            f"""Error inserting {sinan_obj.filename} chunk in database.
                Field causing the error: {
                error_message[field_start_index:field_end_index]
                }\n {e}
            """
        )
        logger.error(err)
        sinan_obj.status = Status.ERROR
        sinan_obj.status_error = err
        sinan_obj.parse_error = False
        Path(sinan_obj.misparsed_file).unlink()
        sinan_obj.misparsed_file = None
        sinan_obj.save()
        return False

    return True
