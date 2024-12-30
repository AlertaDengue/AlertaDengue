from typing import Literal, Optional
from pathlib import Path
from datetime import date

from epiweeks import Week

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from chunked_upload.models import BaseChunkedUpload

from dados.models import City


User = get_user_model()


def sinan_upload_path() -> str:
    return str(Path(settings.DBF_SINAN) / "imported")


def sinan_upload_log_path() -> str:
    return str(Path(settings.DBF_SINAN) / "log")


class SINANChunkedUpload(BaseChunkedUpload):
    user = models.ForeignKey(
        User,
        related_name='uploads',
        on_delete=models.PROTECT
    )


class SINANUploadLogStatus(models.Model):
    STATUS = [
        (0, "Pending"),
        (1, "Success"),
        (2, "Error")
    ]

    status = models.IntegerField(choices=STATUS, default=0, null=False)
    log_file = models.FilePathField(path=sinan_upload_log_path)

    def read_logs(
        self,
        level: Optional[
            Literal["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]
        ] = None,
    ):
        with Path(self.log_file).open(mode='r', encoding="utf-8") as log_file:
            logs = []
            for line in log_file:
                if level:
                    if line.startswith(level):
                        logs.append(line.strip())
                else:
                    logs.append(line.strip())
        return logs

    def _write_logs(
        self,
        level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"],
        message: str,
    ):
        log_message = f"{level}{' ' * (7 - len(level))} - {message}\n"
        with Path(self.log_file).open(mode='a', encoding="utf-8") as log_file:
            log_file.write(log_message)

    def debug(self, message: str):
        self._write_logs(level="DEBUG", message=message)

    def info(self, message: str):
        self._write_logs(level="INFO", message=message)

    def warning(self, message: str):
        self._write_logs(level="WARNING", message=message)

    def fatal(self, error_message: str):
        self._write_logs(level="ERROR", message=error_message)
        self.status = 2
        self.save()

    def done(self, inserts: int):
        filename = SINANUpload.objects.get(status__id=self.id).upload.filename
        message = f"{filename} finished with {inserts} inserts."
        self._write_logs(level="SUCCESS", message=message)
        self.status = 1
        self.save()


class SINANUpload(models.Model):
    UFs = [
        (None, "Brasil"),
        ("AC", "Acre"),
        ("AL", "Alagoas"),
        ("AP", "Amapá"),
        ("AM", "Amazonas"),
        ("BA", "Bahia"),
        ("CE", "Ceará"),
        ("DF", "Distrito Federal"),
        ("ES", "Espírito Santo"),
        ("GO", "Goiás"),
        ("MA", "Maranhão"),
        ("MT", "Mato Grosso"),
        ("MS", "Mato Grosso do Sul"),
        ("MG", "Minas Gerais"),
        ("PA", "Pará"),
        ("PB", "Paraíba"),
        ("PR", "Paraná"),
        ("PE", "Pernambuco"),
        ("PI", "Piauí"),
        ("RJ", "Rio de Janeiro"),
        ("RN", "Rio Grande do Norte"),
        ("RS", "Rio Grande do Sul"),
        ("RO", "Rondônia"),
        ("RR", "Roraima"),
        ("SC", "Santa Catarina"),
        ("SP", "São Paulo"),
        ("SE", "Sergipe"),
        ("TO", "Tocantins"),
    ]

    CID10 = [
        ("A90", "Dengue"),
        ("A92.0", "Chikungunya"),
        ("A928", "Zika")
    ]

    cid10 = models.CharField(max_length=5, null=False, choices=CID10)
    uf = models.CharField(max_length=2, null=True, choices=UFs)
    year = models.IntegerField(null=False)
    upload = models.ForeignKey(
        SINANChunkedUpload,
        on_delete=models.PROTECT,
        null=True,
    )
    status = models.ForeignKey(
        SINANUploadLogStatus,
        on_delete=models.PROTECT,
        null=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.upload.filename}"

    def _final_basename(self):
        filename = str(Path(self.upload.filename).with_suffix(""))
        disease = {
            "A90": "DENG",
            "A92.0": "CHIK",
            "A928": "ZIKA"
        }
        uf = self.uf if self.uf else "BR"
        epiweek = Week.fromdate(self.uploaded_at)
        return "_".join(
            [str(epiweek), disease[self.cid10], uf]
        ) + "-" + filename

    class Meta:
        app_label = "upload"


class SINANUploadHistory(models.Model):
    """
    Stores the History of SINAN inserts on "Municipio"."Notificacao". Each
    objects represent an inserted row (id) and points to SINANUpload
    """
    notificacao_id = models.BigIntegerField(null=False)
    upload = models.ForeignKey(
        SINANUpload,
        on_delete=models.PROTECT,
        related_name="notificacoes",
        null=False
    )
