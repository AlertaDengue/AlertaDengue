import csv
import dask.dataframe as dd
from pathlib import Path
from loguru import logger

from django.utils.translation import gettext_lazy as _
from celery import shared_task
from celery.result import AsyncResult

from .models import SINAN, Status
from .sinan.utils import (
    sinan_drop_duplicates_from_dataframe,
    sinan_parse_fields
)


@shared_task
def process_sinan_file(sinan_pk: str) -> bool:
    sinan = SINAN.objects.get(pk=sinan_pk)

    sinan.status = Status.CHUNKING
    sinan.save()

    fpath = Path(sinan.filepath)

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
        raise NotImplementedError(f"Unknown file type {fpath.suffix}")

    chunks = result.get(follow_parents=True)

    if chunks:
        logger.debug(f"Parsed {len(chunks)} chunks for {sinan.filename}")
        inserted: AsyncResult = insert_sinan_chunk_on_database.delay(  # pyright: ignore
            sinan_pk
        )

        if not inserted.get(follow_parents=True):
            error_msg = f"Chunks insert task for {sinan.filename} failed"
            logger.error(error_msg)
            raise InterruptedError(error_msg)

        return True

    logger.error(f"No chunks parsed for {sinan.filename}")
    return False


@shared_task
def chunk_csv_file(file_path: str, sep: str) -> list[str]:
    ...


@shared_task
def chunk_dbf_file(file_path: str) -> list[str]:
    ...


@shared_task
def insert_sinan_chunks_on_database(sinan_pk: str) -> bool:
    sinan = SINAN.objects.get(pk=sinan_pk)

    logger.debug(f"Inserting {sinan.filename} to database")
    sinan.status = Status.INSERTING
    sinan.save()

    chunks_list = [chunk for chunk in Path(sinan.chunks_dir).glob("*.parquet")]

    try:
        for chunk in chunks_list:
            df = dd.read_parquet(  # pyright: ignore
                str(chunk.absolute()), engine="fastparquet"
            )
            df = sinan_drop_duplicates_from_dataframe(
                df, sinan.filename  # pyright: ignore
            )
            df = sinan_parse_fields(df, sinan)

    except Exception as e:
        logger.error(f"Error reading {sinan.filename} chunks: {str(e)}")
        sinan.status = Status.ERROR
        sinan.save()

        for chunk in chunks_list:
            chunk.unlink(missing_ok=True)

        raise e

    return True
