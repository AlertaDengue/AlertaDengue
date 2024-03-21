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
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from ad_main.settings import get_sqla_conn
from upload.sinan.validations import (
    validate_file_exists,
    validade_file_type,
    validade_year,
    validate_residue_file_exists,
    validate_residue_file_name,
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


class SINAN(models.Model):
    db_engine = get_sqla_conn("dengue")
    table_schema = '"Municipio"."Notificacao"'

    filename = models.CharField(
        primary_key=True,
        null=False,
        blank=False,
        help_text=_("Name of the file with suffix"),
        validators=[validade_file_type],
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
        validators=[validade_year]
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
        default=Status.WAITING_CHUNK,
        help_text=_("Upload status of the file")
    )
    parse_error = models.BooleanField(
        null=False,
        default=False,
        help_text=_(
            "An parse error ocurred when reading data, "
            "moved errored rows to `error_residue` file. "
            "This error doesn't change the status to ERROR"
        ))
    error_residue = models.FileField(
        null=True,
        default=None,
        help_text=_(
            "Absolute CSV file path containing failed rows from data parsing, "
            "before being uploaded to database. The filename format format is "
            "RESIDUE_{filename} and it requires further human verification"
        ),
        validators=[validate_residue_file_name, validate_residue_file_exists]
    )
    uploaded_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True
    )
    uploaded_at = models.DateField(null=False)

    @classmethod
    def create(
        cls,
        filepath: str,
        notification_year: int,
        disease: Diseases = Diseases.DENGUE,
        uf: UFs = UFs.BR,
        municipio: Optional[int] = None,
        status: Status = Status.WAITING_CHUNK,
        parse_error: bool = False,
        error_residue: Optional[str] = None,
        uploaded_by: Optional[User] = None,  # pyright: ignore
        uploaded_at=datetime.now().date
    ):
        file = Path(filepath)

        if not file.is_absolute():
            raise ValidationError("File path must be absolute")

        file = Path(move_file_to_final_destination(
            file_path=str(file.absolute()),
            disease=disease,
            uf=uf,
            notification_year=notification_year,
            export_date=uploaded_at,
            geocode=municipio,
        ))

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

        else:
            raise NotImplementedError(f"Unknown file type {file.suffix}")

        validate_fields(columns)

        sinan = cls(
            filename=file.name,
            filepath=file.absolute(),
            disease=disease,
            notification_year=notification_year,
            uf=uf,
            municipio=municipio,
            status=status,
            parse_error=parse_error,
            error_residue=error_residue,
            uploaded_by=uploaded_by,
            uploaded_at=uploaded_at
        )

        return sinan

    @property
    def chunks_dir(self):
        fname = Path(self.filename)
        dir = Path(
            os.path.join(
                settings.MEDIA_ROOT,
                fname.name.removesuffix(fname.suffix))
        )
        dir.mkdir(exist_ok=True, parents=True)
        return dir.absolute()

    def parse(self):
        self.status = Status.CHUNKING
        self.save()

        fpath = Path(self.filepath)

        try:
            if fpath.suffix == ".csv":
                sniffer = csv.Sniffer()
                with open(self.filepath, "r") as f:
                    data = f.read(10240)
                    sep = sniffer.sniff(data).delimiter
                ...  # TODO:
            elif fpath.suffix == ".dbf":
                ...  # TODO:
            else:
                raise NotImplementedError(f"Unknown file type {fpath.suffix}")

        except Exception as e:
            self.status = Status.ERROR
            self.save()

            chunks_dir = Path(self.chunks_dir)

            for chunk in list(chunks_dir.glob("*.parquet")):
                chunk.unlink(missing_ok=True)

            raise e

        return self

    def upload(self):
        if self.status != Status.WAITING_INSERT:
            raise ValueError("Chunks are not ready to insert")

        self.status = Status.INSERTING
        self.save()

        try:
            ...  # TODO
        except Exception as e:
            self.status = Status.ERROR
            self.save()

            raise e


def move_file_to_final_destination(
    file_path: str,
    disease: str,
    uf: str,
    notification_year: int,
    export_date: date,
    geocode: Optional[int] = None,
) -> str:
    if not settings.DBF_SINAN:
        raise NotADirectoryError("DBF_SINAN directory is None")

    dest_dir = Path(settings.DBF_SINAN) / "imported"

    dest_dir.mkdir(exist_ok=True, parents=True)

    file = Path(file_path)

    if not file.is_absolute():
        raise ValueError(f"{str(file)} path is not abosule")

    if not file.exists():
        raise FileNotFoundError(f"{str(file)} not found")

    dest_filename = "-".join(list(filter(
        lambda x: x,  # filters out None's
        [uf, disease, str(geocode), str(notification_year), str(export_date)]
    ))) + file.suffix.lower()

    dest = dest_dir / dest_filename

    shutil.move(str(file.absolute()), str(dest.absolute()))

    return str(dest.absolute())
