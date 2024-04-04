import os
import csv
from pathlib import Path
from django.core.mail import send_mail

import pandas as pd
import geopandas as gpd
import dask.dataframe as dd
from loguru import logger
from celery import shared_task
from celery.result import AsyncResult
from simpledbf import Dbf5

from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .models import SINAN, Status
from .sinan.utils import (
    sinan_drop_duplicates_from_dataframe,
    sinan_parse_fields,
    chunk_gen
)


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
            raise NotImplementedError(f"Unknown file type {fpath.suffix}")

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
            error_msg = f"Chunks insert task for {sinan.filename} failed"
            logger.error(error_msg)
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

    columns = []

    for chunk in chunks_list:
        try:
            df: dd = dd.read_parquet(  # pyright: ignore
                str(chunk.absolute()),
                engine="fastparquet"
            )
        except Exception as e:
            misparsed_csv_file.unlink(missing_ok=True)
            sinan.status = Status.ERROR
            sinan.misparsed_file = None
            sinan.status_error = f"Error reading chunks: {e}"
            sinan.save()
            return False

        columns = list(df.columns)  # pyright: ignore

        df = sinan_drop_duplicates_from_dataframe(
            df,  # pyright: ignore
            sinan.filename
        )

        df = sinan_parse_fields(
            df,  # pyright: ignore
            sinan
        )

    pd.DataFrame(columns=columns).to_csv(misparsed_csv_file, index=False)

    if sinan.status == Status.FINISHED_MISPARSED:
        # send_mail() # TODO: send mail with link to misparsed csv file
        ...
    else:
        misparsed_csv_file.unlink(missing_ok=True)
        sinan.misparsed_file = None
        sinan.save()

    return True
