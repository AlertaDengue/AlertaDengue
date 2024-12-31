import shutil
import time
from pathlib import Path
from typing import Iterator, Tuple

import pyarrow.parquet as pq
import geopandas as gpd
import pandas as pd
from celery import shared_task
from psycopg2.extras import DictCursor
from simpledbf import Dbf5

from ad_main.settings import get_sqla_conn

from .models import (
    sinan_upload_path,
    SINANUpload,
    SINANUploadFatalError,
    SINANUploadHistory
)
from .sinan.utils import chunk_gen, parse_data


ENGINE = get_sqla_conn(database="dengue")


@shared_task
def sinan_process_file(upload_sinan_id: int):
    sinan = SINANUpload.objects.get(pk=upload_sinan_id)
    sinan.status.debug("Task 'process_sinan_file' started.")
    sinan_move_file(upload_sinan_id)
    sinan_verify_file(upload_sinan_id)
    inserted_rows = sinan_insert_to_db(upload_sinan_id)
    sinan.status.done(inserted_rows)


@shared_task
def sinan_move_file(upload_sinan_id: int):
    sinan = SINANUpload.objects.get(pk=upload_sinan_id)
    sinan.status.debug("Task 'move_sinan_file' started.")
    try:
        file = Path(sinan.upload.file.path)
        if not file.exists():
            raise SINANUploadFatalError(
                sinan.status,
                "SINAN Upload file not found"
            )
        dest = Path(sinan_upload_path()) / sinan._final_basename()
        dest = dest.with_suffix(Path(sinan.upload.filename).suffix)
        shutil.move(str(file), str(dest))
        sinan.upload.file.name = str(dest)
        sinan.upload.filename = sinan._final_basename()
        sinan.upload.save()
        sinan.status.debug(f"File moved to {str(dest)}")
        sinan.status.debug("Task 'move_sinan_file' finished.")
    except Exception as e:
        raise SINANUploadFatalError(sinan.status, e)


@shared_task
def sinan_verify_file(upload_sinan_id: int):
    sinan = SINANUpload.objects.get(pk=upload_sinan_id)
    sinan.status.debug("Task 'sinan_verify_file' started.")
    file = Path(sinan.upload.file.path)

    try:
        if file.suffix.lower() == ".parquet":
            columns = pq.read_schema(str(file)).names
        elif file.suffix.lower() == ".dbf":
            columns = gpd.read_file(
                sinan.upload.file.path,
                rows=0,
                ignore_geometry=True,
            ).columns
        elif file.suffix.lower() == ".csv":
            columns = pd.read_csv(str(file), nrows=0).columns
        else:
            raise SINANUploadFatalError(
                sinan.status, f"File type '{file.suffix}' is not supported"
            )
    except Exception as e:
        err = f"Could not read {sinan.upload.filename} columns: {e}"
        raise SINANUploadFatalError(sinan.status, err)

    for col, synonym in sinan.SYNONYMS_FIELDS.items():
        try:
            if not col in columns:
                if synonym in columns:
                    for i, req in enumerate(sinan.REQUIRED_COLS):
                        if req == col:
                            sinan.REQUIRED_COLS[i] = synonym

                    cols = sinan.COLUMNS.copy()
                    for column, final_col in sinan.COLUMNS:
                        if column == col:
                            del cols[column]
                            cols[synonym] = final_col
                    sinan.COLUMNS = cols
                    sinan.save()
        except:
            sinan.status.warning(
                f"Could not use the synonym '{synonym}' of the field '{col}'"
            )

    if not all(col in columns for col in sinan.REQUIRED_COLS):
        missing_cols = set(sinan.REQUIRED_COLS).difference(set(columns))
        err = f"Missing required columns: {missing_cols}"
        raise SINANUploadFatalError(sinan.status, err)

    if not all(col in columns for col in sinan.COLUMNS):
        missing_cols = set(sinan.COLUMNS).difference(set(columns))
        warning = f"Missing columns (filled with <NA>): {missing_cols}"
        sinan.status.warning(warning)

    sinan.status.debug("Task 'sinan_verify_file' finished.")


def insert_chunk_to_temp_table(
    upload_sinan_id: int,
    df_chunk: pd.DataFrame,
    tablename: str,
    cursor,
):
    sinan = SINANUpload.objects.get(pk=upload_sinan_id)
    columns = list(sinan.COLUMNS.values())

    insert_sql = (
        f"INSERT INTO {tablename}({','.join(columns)}) "
        f"VALUES ({','.join(['%s' for _ in columns])}) "
        f"ON CONFLICT ON CONSTRAINT casos_unicos DO UPDATE SET "
        f"{','.join([f'{j}=excluded.{j}' for j in columns])}"
    )
    try:
        df_chunk = parse_data(df_chunk, sinan.cid10, sinan.year)
        df_chunk = df_chunk.replace({pd.NA: None})
        df_chunk = df_chunk.rename(columns=sinan.COLUMNS)
        rows = [
            tuple(row)
            for row in df_chunk.itertuples(index=False)
        ]
        cursor.executemany(insert_sql, rows)
    except Exception as e:
        raise SINANUploadFatalError(
            sinan.status,
            f"Error inserting chunk into temporary table: {e}"
        )


def insert_temp_to_notificacao(
    cursor,
    temp_table,
    columns: list[str]
) -> (int, int):
    fields = ",".join(columns)
    on_conflict = ",".join([f"{field}=excluded.{field}" for field in columns])

    cursor.execute('SELECT MAX(id) FROM "Municipio"."Notificacao";')
    start_id = cursor.fetchone()[0]

    insert_sql = (
        f'INSERT INTO "Municipio"."Notificacao" ({fields}) '
        f"SELECT {fields} FROM {temp_table}"
        f"ON CONFLICT ON CONSTRAINT casos_unicos DO UPDATE SET {on_conflict}"
    )

    cursor.execute(insert_sql)

    cursor.execute('SELECT MAX(id) FROM "Municipio"."Notificacao";')
    end_id = cursor.fetchone()[0]

    return start_id + 1, end_id


@shared_task
def sinan_insert_to_db(upload_sinan_id: int):
    sinan = SINANUpload.objects.get(pk=upload_sinan_id)
    sinan.status.debug("Task 'sinan_insert_to_db' started.")

    st = time.time()
    file = Path(sinan.upload.file.path)
    temp_table = f"temp_sinan_upload_{sinan.pk}"
    chunksize = 100000
    inserted_rows = 0

    with ENGINE.begin() as conn:
        cursor = conn.connection.cursor(cursor_factory=DictCursor)
        cursor.execute(f"""
            CREATE TEMP TABLE {temp_table} (
                dt_notific DATE,
                se_notif INTEGER,
                ano_notif INTEGER,
                dt_sin_pri DATE,
                se_sin_pri INTEGER,
                dt_digita DATE,
                municipio_geocodigo INTEGER,
                nu_notific INTEGER,
                cid10_codigo VARCHAR(5),
                dt_nasc DATE,
                cs_sexo VARCHAR(1),
                nu_idade_n INTEGER,
                resul_pcr NUMERIC,
                criterio NUMERIC,
                classi_fin NUMERIC,
                dt_chik_s1 DATE,
                dt_chik_s2 DATE,
                dt_prnt DATE,
                res_chiks1 VARCHAR(255),
                res_chiks2 VARCHAR(255),
                resul_prnt VARCHAR(255),
                dt_soro DATE,
                resul_soro VARCHAR(255),
                dt_ns1 DATE,
                resul_ns1 VARCHAR(255),
                dt_viral DATE,
                resul_vi_n VARCHAR(255),
                dt_pcr DATE,
                sorotipo VARCHAR(255),
                id_distrit NUMERIC,
                id_bairro NUMERIC,
                nm_bairro VARCHAR(255),
                id_unidade NUMERIC
            );
        """)
        sinan.status.debug(f"{temp_table} created.")
        try:
            if file.suffix.lower() == ".parquet":
                reader = pq.ParquetFile(str(file))
                for batch in reader.iter_batches(
                    batch_size=chunksize,
                    columns=list(sinan.COLUMNS)
                ):
                    df_chunk = batch.to_pandas()
                    insert_chunk_to_temp_table(
                        upload_sinan_id,
                        df_chunk,
                        temp_table,
                        conn
                    )
                    inserted_rows += len(df_chunk)
            elif file.suffix.lower() == ".csv":
                for chunk in pd.read_csv(
                    str(file),
                    chunksize=chunksize,
                    usecols=list(sinan.COLUMNS)
                ):
                    insert_chunk_to_temp_table(
                        upload_sinan_id,
                        chunk,
                        temp_table,
                        conn
                    )
                    inserted_rows += len(chunk)
            elif file.suffix.lower() == ".dbf":
                dbf = Dbf5(str(file), codec="iso-8859-1")
                for chunk, (lowerbound, upperbound) in enumerate(
                    chunk_gen(chunksize, dbf.numrec)
                ):
                    chunk = gpd.read_file(
                        str(file),
                        include_fields=list(sinan.COLUMNS),
                        rows=slice(lowerbound, upperbound),
                        ignore_geometry=True,
                    )
                    insert_chunk_to_temp_table(
                        upload_sinan_id,
                        chunk,
                        temp_table,
                        conn
                    )
                    inserted_rows += len(chunk)
            else:
                raise SINANUploadFatalError(
                    sinan.status, f"File type '{file.suffix}' is not supported"
                )

            stard_id, end_id = insert_temp_to_notificacao(
                cursor,
                temp_table,
                list(sinan.COLUMNS.values())
            )

            for id in range(stard_id, end_id + 1):
                SINANUploadHistory.objects.create(
                    notificacao_id=id,
                    upload=sinan,
                )

        except Exception as e:
            raise SINANUploadFatalError(
                sinan.status, f"Error inserting {file.name} into db: {e}"
            )
        finally:
            cursor.execute(f"DROP TABLE IF EXISTS {temp_table};")
            sinan.status.debug(f"{temp_table} created.")

        et = time.time()
        sinan.status.debug(
            f"Task 'sinan_insert_to_db' finished with {st-et} seconds."
        )
        return inserted_rows
