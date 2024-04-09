import shutil
import os
import csv
from pathlib import Path
from typing import Optional
from datetime import (datetime, date)
import pandas as pd
from simpledbf import Dbf5

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from ad_main.settings import get_sqla_conn
from upload.sinan.validations import (
    validate_file_exists,
    validate_file_type,
    validate_year,
    validate_fields,
)


User = get_user_model()


class UFs(models.TextChoices):
    BR = "BR", "Brasil"  # pyright: ignore
    AC = "AC", "Acre"  # pyright: ignore
    AL = "AL", "Alagoas"  # pyright: ignore
    AP = "AP", "Amapá"  # pyright: ignore
    AM = "AM", "Amazonas"  # pyright: ignore
    BA = "BA", "Bahia"  # pyright: ignore
    CE = "CE", "Ceará"  # pyright: ignore
    ES = "ES", "Espírito Santo"  # pyright: ignore
    GO = "GO", "Goiás"  # pyright: ignore
    MA = "MA", "Maranhão"  # pyright: ignore
    MT = "MT", "Mato Grosso"  # pyright: ignore
    MS = "MS", "Mato Grosso do Sul"  # pyright: ignore
    MG = "MG", "Minas Gerais"  # pyright: ignore
    PA = "PA", "Pará"  # pyright: ignore
    PB = "PB", "Paraíba"  # pyright: ignore
    PR = "PR", "Paraná"  # pyright: ignore
    PE = "PE", "Pernambuco"  # pyright: ignore
    PI = "PI", "Piauí"  # pyright: ignore
    RJ = "RJ", "Rio de Janeiro"  # pyright: ignore
    RN = "RN", "Rio Grande do Norte"  # pyright: ignore
    RS = "RS", "Rio Grande do Sul"  # pyright: ignore
    RO = "RO", "Rondônia"  # pyright: ignore
    RR = "RR", "Roraima"  # pyright: ignore
    SC = "SC", "Santa Catarina"  # pyright: ignore
    SP = "SP", "São Paulo"  # pyright: ignore
    SE = "SE", "Sergipe"  # pyright: ignore
    TO = "TO", "Tocantins"  # pyright: ignore
    DF = "DF", "Distrito Federal"  # pyright: ignore


class Diseases(models.TextChoices):
    DENGUE = "dengue", "Dengue"  # pyright: ignore
    CHIK = "chik", "Chigungunya"  # pyright: ignore
    ZIKA = "zika", "Zika"  # pyright: ignore


class Status(models.TextChoices):
    WAITING_CHUNK = "waiting_chunk", _("Aguardando chunk")  # pyright: ignore
    CHUNKING = "chunking", _("Processando chunks")  # pyright: ignore
    WAITING_INSERT = "waiting_insert", _(
        "Aguardando inserção"
    )  # pyright: ignore
    INSERTING = "inserting", _("Inserindo dados")  # pyright: ignore
    ERROR = "error", _("Erro")  # pyright: ignore
    FINISHED = "finished", _("Finalizado")  # pyright: ignore
    FINISHED_MISPARSED = "finished_misparsed", _(
        "Finalizado com erro"
    )  # pyright: ignore


class SINAN(models.Model):
    db_engine = get_sqla_conn("dengue")
    table_schema = '"Municipio"."Notificacao"'

    id = models.AutoField(primary_key=True)
    filename = models.CharField(
        null=False,
        blank=False,
        help_text=_("Name of the file with suffix"),
        validators=[validate_file_type],
        max_length=100
    )
    filepath = models.FileField(
        null=True,
        blank=False,
        help_text=_("Absolute data file path, Null if deleted after insert"),
        validators=[validate_file_exists]
    )
    disease = models.CharField(
        choices=Diseases.choices,
        default=Diseases.DENGUE,
        max_length=50
    )
    notification_year = models.IntegerField(
        null=False,
        validators=[validate_year]
    )
    uf = models.CharField(
        max_length=2,
        null=False,
        choices=UFs.choices,
        default=UFs.BR
    )
    municipio = models.IntegerField(null=True)
    status = models.TextField(
        null=False,
        choices=Status.choices,
        help_text=_("Upload status of the file")
    )
    status_error = models.TextField(
        null=True,
        blank=False,
        help_text=_(
            "If Status ERROR, the traceback will be stored in status_error"
        )
    )
    parse_error = models.BooleanField(
        null=False,
        default=False,
        help_text=_(
            "An parse error ocurred when reading data, "
            "moved errored rows to `misparsed_file` file. "
            "This error doesn't change the status to ERROR"
        ))
    misparsed_file = models.FileField(
        null=True,
        default=None,
        help_text=_(
            "Absolute CSV file path containing failed rows from data parsing, "
            "before being uploaded to database. The filename format format is "
            "MISPARSED_{filename} and it requires further human verification"
        ),
    )
    misparsed_cols = models.JSONField(
        default=list,
        help_text=_("Name of the columns containing misparsed rows"),
    )
    inserted_rows = models.IntegerField(
        default=0,
        help_text=_("Amount of inserted rows in database"),
    )
    uploaded_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateField(null=False)

    def __str__(self):
        return str(self.filename)

    @classmethod
    def create(
        cls,
        filepath: str,
        notification_year: int,
        disease: Diseases = Diseases.DENGUE,
        uf: UFs = UFs.BR,
        municipio: Optional[int] = None,
        status: Status = Status.WAITING_CHUNK,
        status_error: Optional[str] = None,
        parse_error: bool = False,
        misparsed_file: Optional[str] = None,
        uploaded_by: Optional[User] = None,  # pyright: ignore
        uploaded_at=datetime.now().date()
    ):
        file = Path(str(filepath))

        if not file:
            raise ValueError(f"Error reading file {str(file)}")

        if not file.is_absolute():
            raise ValueError("File path must be absolute")

        if not file.exists():
            raise FileNotFoundError(f"{file} not found")

        if file.is_dir():
            raise ValueError(f"{file} is a directory")

        if file.suffix.lower() not in [".dbf", ".csv", ".parquet"]:
            raise ValueError(f"Unkown file type {file.suffix}")

        file = Path(move_file_to_final_destination(
            file_path=str(file.absolute()),
            disease=disease,
            uf=uf,
            notification_year=notification_year,
            export_date=uploaded_at,
            geocode=municipio,
        ))

        columns: list = []
        try:
            if file.suffix == ".csv":
                sniffer = csv.Sniffer()

                with open(file.absolute(), "r", newline='') as f:
                    data = f.read(10240)
                    sep = sniffer.sniff(data).delimiter

                columns = pd.read_csv(
                    file.absolute(),
                    index_col=0,
                    nrows=0,
                    sep=sep
                ).columns.to_list()

            elif file.suffix == ".dbf":
                dbf = Dbf5(file.absolute(), codec="iso-8859-1")
                columns = [col[0] for col in dbf.fields]

            elif file.suffix == ".parquet":
                raise NotImplementedError("TODO")  # TODO

            else:
                raise NotImplementedError(f"Unknown file type {file.suffix}")

        except Exception as e:
            status = Status.ERROR
            status_error = f"Data fields could not be extracted: {e}"

        try:
            validate_fields(columns)
        except Exception as e:
            status = Status.ERROR
            status_error = f"Invalid data field(s) error: {e}"

        sinan = cls(
            filename=file.name,
            filepath=str(file.absolute()),
            disease=disease,
            notification_year=notification_year,
            uf=uf,
            municipio=municipio,
            status=status,
            status_error=status_error,
            parse_error=parse_error,
            misparsed_file=misparsed_file,
            uploaded_by=uploaded_by,
            uploaded_at=uploaded_at
        )

        return sinan

    @property
    def chunks_dir(self) -> str | None:
        if self.filepath:
            fname = Path(str(self.filename))
            dir = Path(
                os.path.join(
                    settings.DBF_SINAN,
                    "chunks",
                    fname.name.removesuffix(fname.suffix))
            )
            dir.mkdir(exist_ok=True, parents=True)
            return str(dir.absolute())


def move_file_to_final_destination(
    file_path: str,
    disease: str,
    uf: str,
    notification_year: int,
    export_date: date,
    dest_dir: Optional[Path] = Path(settings.DBF_SINAN) / "imported",
    geocode: Optional[int] = None,
) -> str:
    if not settings.DBF_SINAN:
        raise NotADirectoryError("DBF_SINAN directory is None")

    if not dest_dir or not dest_dir.exists():
        raise NotADirectoryError("dest_dir must be specified")

    dest_dir.mkdir(exist_ok=True, parents=True)

    file = Path(str(file_path))

    if not file.is_absolute():
        raise ValueError(f"{str(file)} path is not abosule")

    if not file.exists():
        raise FileNotFoundError(f"{str(file)} not found")

    random_id = int(str(datetime.now().timestamp())[-4:])

    file_specs = [
        uf,
        disease.upper(),
        str(geocode) if geocode else None,
        str(notification_year),
        str(export_date),
        str(random_id)
    ]

    dest_filename = "-".join(
        [s for s in file_specs if s is not None]
    ) + file.suffix.lower()

    dest = dest_dir / dest_filename

    shutil.move(str(file.absolute()), str(dest.absolute()))

    return str(dest.absolute())
