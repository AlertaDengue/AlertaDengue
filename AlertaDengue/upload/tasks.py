import os
import csv
from pathlib import Path
from django.core.mail import send_mail

import pandas as pd
import geopandas as gpd
import dask.dataframe as dd
from loguru import logger
from simpledbf import Dbf5
from celery import shared_task
from celery.result import AsyncResult, allow_join_result
from psycopg2.extras import DictCursor

from django.utils.translation import gettext_lazy as _
from django.conf import settings

from ad_main.settings import get_sqla_conn
from .models import SINAN, Status
from .sinan.utils import (
    EXPECTED_FIELDS,
    sinan_drop_duplicates_from_dataframe,
    sinan_parse_fields,
    chunk_gen
)

DB_ENGINE = get_sqla_conn(database="dengue")


@shared_task
def process_sinan_file(sinan_pk: int) -> bool:
    sinan = SINAN.objects.get(pk=sinan_pk)
    fpath = Path(str(sinan.filepath))

    try:
        if fpath.suffix == ".csv":
            sniffer = csv.Sniffer()

            with open(fpath, "r") as f:
                data = f.read(10240)
                sep = sniffer.sniff(data).delimiter

            result: AsyncResult = chunk_csv_file.delay(  # pyright: ignore
                sinan.pk
            )

        elif fpath.suffix == ".dbf":
            result: AsyncResult = chunk_dbf_file.delay(  # pyright: ignore
                sinan.pk
            )

        else:
            err = f"Unknown file type {fpath.suffix}"
            logger.error(err)
            sinan.status = Status.ERROR
            sinan.status_error = err
            sinan.save(update_fields=['status', 'status_error'])
            return False

    except Exception as e:
        sinan.status = Status.ERROR
        sinan.status_error = f"Error chunking file: {e}"
        sinan.save(update_fields=['status', 'status_error'])
        return False

    with allow_join_result():
        chunks = result.get(follow_parents=True)

        if chunks:
            sinan.save(update_fields=['status', 'status_error'])
            logger.info(
                "Parsed "
                f"{len(list(Path(str(sinan.chunks_dir)).glob('*.parquet')))} "
                f"chunks for {sinan.filename}"
            )
            inserted: AsyncResult = (
                parse_insert_chunks_on_database
                .delay(sinan_pk)  # pyright: ignore
            )

            if not inserted.get(follow_parents=True):
                logger.error(f"No data inserted for {sinan.filename}")
                sinan.status = Status.ERROR
                sinan.status_error = f"No data were parsed"
                sinan.save(update_fields=['status', 'status_error'])
                return False
            return True
        else:
            logger.error(f"No chunks parsed for {sinan.filename}")
            sinan.status = Status.ERROR
            sinan.status_error = f"No chunks were parsed"
            sinan.save(update_fields=['status', 'status_error'])
    return False


@shared_task
def chunk_csv_file(sinan_pk: int) -> bool:
    ...
    return False


@shared_task
def chunk_dbf_file(sinan_pk: int) -> bool:
    sinan = SINAN.objects.get(pk=sinan_pk)

    if sinan.status == Status.WAITING_CHUNK:
        sinan.status = Status.CHUNKING
        sinan.save(update_fields=['status'])

        logger.info("Converting DBF file to Parquet chunks")
        dbf = Dbf5(str(sinan.filepath), codec="iso-8859-1")
        dbf_name = str(dbf.dbf)[:-4]

        if not os.path.exists(str(sinan.filepath)):
            raise FileNotFoundError(f"{str(sinan.filepath)} does not exist")

        for chunk, (lowerbound, upperbound) in enumerate(
            chunk_gen(1000, dbf.numrec)
        ):
            parquet_fname = os.path.join(
                str(sinan.chunks_dir), f"{dbf_name}-{chunk}.parquet"
            )
            df = gpd.read_file(
                str(sinan.filepath),
                include_fields=list(EXPECTED_FIELDS.values()),
                rows=slice(lowerbound, upperbound),
                ignore_geometry=True,
            )

            missing_cols = list(
                set(EXPECTED_FIELDS.values()).difference(set(df.columns))
            )

            if missing_cols:
                for column in missing_cols:
                    df[column] = None

            df.to_parquet(parquet_fname)

        sinan.status = Status.WAITING_INSERT
        sinan.save(update_fields=['status'])
        return True
    else:
        logger.info(
            f"Invalid Status to chunk SINAN object: {sinan.status}"
        )
        return False


@shared_task
def parse_insert_chunks_on_database(sinan_pk: int) -> bool:
    sinan = SINAN.objects.get(pk=sinan_pk)

    misparsed_csv_file = (
        Path(str(settings.DBF_SINAN)) / "residue_csvs" /
        f"RESIDUE_{Path(str(sinan.filename)).with_suffix('.csv')}"
    )

    misparsed_csv_file.touch()

    sinan.misparsed_file = str(misparsed_csv_file.absolute())
    sinan.status = Status.INSERTING
    sinan.save(update_fields=['misparsed_file', 'status'])

    if sinan.chunks_dir:
        chunks_list = list(Path(sinan.chunks_dir).glob("*.parquet"))
    else:
        err = f"Error creating chunks dir for {sinan.filename}"
        logger.error(err)
        sinan.status = Status.ERROR
        sinan.status_error = err
        sinan.save(update_fields=['status', 'status_error'])
        return False

    uploaded_rows: int = 0
    with DB_ENGINE.begin() as conn:  # pyright: ignore
        # TODO: this could be ran asynchronously
        for chunk in chunks_list:
            try:
                df: dd = dd.read_parquet(  # pyright: ignore
                    str(chunk.absolute()),
                    engine="fastparquet"
                )
            except Exception as e:
                err = f"Error reading chunks for {sinan.filename}: {e}"
                logger.error(err)
                if misparsed_csv_file:
                    misparsed_csv_file.unlink(missing_ok=True)
                    sinan.misparsed_file = None
                sinan.status = Status.ERROR
                sinan.status_error = err
                sinan.save(
                    update_fields=['status', 'misparsed_file', 'status_error']
                )
                return False

            try:
                df = sinan_drop_duplicates_from_dataframe(
                    df.compute(),  # pyright: ignore
                    sinan.filename
                )
            except Exception as e:
                err = f"Error dropping duplicates from {sinan.filename}: {e}"
                logger.error(err)
                sinan.status = Status.ERROR
                sinan.status_error = err
                sinan.save(update_fields=['status', 'status_error'])
                return False

            # Can't throw any exception. Return False instead
            df = sinan_parse_fields(
                df,  # pyright: ignore
                sinan
            )

            # Can't throw any exception. Return number of inserted rows
            uploaded_rows += save_to_pgsql(
                df,  # pyright: ignore
                sinan,
                conn
            )

        if uploaded_rows:
            logger.info(
                f"Inserting {uploaded_rows} rows from {sinan.filename}"
            )

            if sinan.parse_error:
                sinan.status = Status.FINISHED_MISPARSED
                sinan.save(update_fields=['status'])
                # send_mail() # TODO: send mail with link to misparsed csv file
                return True
            else:
                sinan.status = Status.FINISHED
                if misparsed_csv_file:
                    misparsed_csv_file.unlink(missing_ok=True)
                    sinan.misparsed_file = None
                sinan.save(update_fields=['status', 'misparsed_file'])
                # send_mail(): # TODO: send successful insert email
                return True
        else:
            # send_mail(): # TODO: send failed insert email
            return False


def save_to_pgsql(
    df: pd.DataFrame, sinan_obj: SINAN, conn
) -> int:
    """
    Return the number of rows executed by INSERT. Can't throw any Exception
    """
    try:
        cursor = conn.connection.cursor(cursor_factory=DictCursor)

        expected_cols = {v: k for k, v in EXPECTED_FIELDS.items()}
        cols = [expected_cols[c] for c in list(df.columns)]

        insert_sql = (
            f"INSERT INTO {sinan_obj.table_schema}"
            f"({','.join(cols)}) "
            f"VALUES ({','.join(['%s' for _ in cols])}) "
            f"ON CONFLICT ON CONSTRAINT casos_unicos DO UPDATE SET "
            f"{','.join([f'{j}=excluded.{j}' for j in cols])}"
        )

        rows = [
            tuple(row)
            for row in df.itertuples(index=False)
        ]

        cursor.executemany(insert_sql, rows)
        conn.connection.commit()
    except Exception as e:
        conn.connection.rollback()
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
        sinan_obj.save(update_fields=['status', 'status_error', 'parse_error'])
        return 0

    return len(df)
