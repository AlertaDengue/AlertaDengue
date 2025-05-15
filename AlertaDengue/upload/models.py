import pickle
from array import array
from datetime import date
from pathlib import Path
from typing import Generator, Literal, Optional, Union

import pandas as pd

from chunked_upload.models import BaseChunkedUpload
from dados.models import City
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from epiweeks import Week

from .sinan.utils import UF_CODES, chunk_gen

User = get_user_model()


def sinan_upload_path() -> str:
    return str(Path(settings.DBF_SINAN) / "imported")


def sinan_upload_log_path() -> str:
    return str(Path(settings.DBF_SINAN) / "log")


class SINANChunkedUpload(BaseChunkedUpload):
    user = models.ForeignKey(
        User, related_name="uploads", on_delete=models.PROTECT
    )


class SINANUploadLogStatus(models.Model):
    STATUS = [(0, "Pending"), (1, "Success"), (2, "Error")]

    LOG_LEVEL = ["PROGRESS", "DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]

    status = models.IntegerField(choices=STATUS, default=0, null=False)
    log_file = models.FilePathField(path=sinan_upload_log_path)
    inserts_file = models.FilePathField(path=sinan_upload_log_path, null=True)
    updates_file = models.FilePathField(path=sinan_upload_log_path, null=True)
    residues_file = models.FilePathField(path=sinan_upload_log_path, null=True)

    def _read_ids(self, id_type: Literal["inserts", "updates"]) -> array:
        ids_file = Path(sinan_upload_log_path()) / f"{self.pk}.{id_type}.log"

        if not ids_file.exists():
            return array("i", [])

        with ids_file.open("rb") as log:
            ids = pickle.load(log)

        return ids

    @property
    def inserts(self) -> int:
        return len(self._read_ids("inserts"))

    @property
    def updates(self) -> int:
        return len(self._read_ids("updates"))

    def contains_residue(self) -> bool:
        if self.residues_file and Path(self.residues_file.exists()):
            try:
                df = pd.read_csv(self.residues_file)
                if len(df) > 0:
                    return True
            except Exception:
                self.warning(
                    f"Couldn't open {self.residues_file}."
                    "Please contact the moderation"
                )
        return False

    def list_ids(
        self, offset: int, limit: int, id_type: Literal["inserts", "updates"]
    ) -> list[int]:
        if abs(limit - offset) > 50000:
            raise ValueError("ids range exceeds 50_000 entries")

        ids = self._read_ids(id_type)

        if len(ids) == 0:
            return []

        start, end = min([offset, limit]), max([offset, limit])
        return ids[start: end + 1]

    @property
    def time_spend(self) -> float:
        for log in self.read_logs(level="DEBUG"):
            if "time_spend: " in log:
                _, time_spend = log.split("time_spend: ")
                return float(time_spend)
        raise ValueError("No time_spend found in logs")

    def write_inserts(self, insert_ids: list[int]):
        log_dir = Path(sinan_upload_log_path())
        inserts_file = log_dir / f"{self.pk}.inserts.log"
        inserts_file.touch()
        inserts = array("i", insert_ids)
        with inserts_file.open("wb") as log:
            pickle.dump(inserts, log)
        self.inserts_file = inserts_file
        self.save()

    def write_updates(self, updates_ids: list[int]):
        log_dir = Path(sinan_upload_log_path())
        updates_file = log_dir / f"{self.pk}.updates.log"
        updates_file.touch()
        updates = array("i", updates_ids)
        with updates_file.open("wb") as log:
            pickle.dump(updates, log)
        self.updates_file = updates_file
        self.save()

    def read_logs(
        self,
        level: Optional[
            Literal["PROGRESS", "DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"]
        ] = None,
        only_level: bool = False,
    ):
        with Path(self.log_file).open(mode="r", encoding="utf-8") as log_file:
            logs = []

            for line in log_file:
                if level:
                    startswith = (
                        tuple(self.LOG_LEVEL[self.LOG_LEVEL.index(level):])
                        if not only_level
                        else level
                    )
                    if line.startswith(startswith):
                        logs.append(line.strip())
                else:
                    logs.append(line.strip())
        return logs

    def _write_logs(
        self,
        level: Literal[
            "PROGRESS", "DEBUG", "INFO", "WARNING", "ERROR", "SUCCESS"
        ],
        message: str,
    ):
        try:
            spaces = " " * (max(map(len, self.LOG_LEVEL)) - len(level))
        except TypeError:
            spaces = " " * len("PROGRESS")

        if self.status == 2:
            raise ValueError("Log is closed for writing (finished with error)")
        log_message = f"{level}{spaces} - {message}\n"
        with Path(self.log_file).open(mode="a", encoding="utf-8") as log_file:
            log_file.write(log_message)

    def debug(self, message: str):
        self._write_logs(level="DEBUG", message=message)

    def progress(self, rowcount: int, total_rows: int):
        percentage = f"{min((rowcount / total_rows) * 100, 100):.2f}%"
        self._write_logs(level="PROGRESS", message=percentage)

    def info(self, message: str):
        self._write_logs(level="INFO", message=message)

    def warning(self, message: str):
        self._write_logs(level="WARNING", message=message)

    def fatal(self, error_message: str):
        self._write_logs(level="ERROR", message=error_message)
        self.status = 2
        self.save()

    def done(self, inserts: int, time_spend: float):
        filename = SINANUpload.objects.get(status__id=self.id).upload.filename
        message = f"{inserts} inserts in {time_spend:.2f} seconds."
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

    CID10 = [("A90", "Dengue"), ("A92.0", "Chikungunya"), ("A928", "Zika")]

    REQUIRED_COLS = [
        "ID_MUNICIP",
        "ID_AGRAVO",
        "DT_SIN_PRI",
        "DT_NOTIFIC",
        "DT_DIGITA",
        "DT_NASC",
        "NU_ANO",
        "NU_IDADE_N",
        "NU_NOTIFIC",
        "SEM_NOT",
        "SEM_PRI",
        "CS_SEXO",
    ]

    SYNONYMS_FIELDS = {"ID_MUNICIP": ["ID_MN_RESI"]}

    COLUMNS = {
        "DT_NOTIFIC": "dt_notific",
        "SEM_NOT": "se_notif",
        "NU_ANO": "ano_notif",
        "DT_SIN_PRI": "dt_sin_pri",
        "SEM_PRI": "se_sin_pri",
        "DT_DIGITA": "dt_digita",
        "ID_MUNICIP": "municipio_geocodigo",
        "NU_NOTIFIC": "nu_notific",
        "ID_AGRAVO": "cid10_codigo",
        "DT_NASC": "dt_nasc",
        "CS_SEXO": "cs_sexo",
        "NU_IDADE_N": "nu_idade_n",
        "RESUL_PCR_": "resul_pcr",
        "CRITERIO": "criterio",
        "CLASSI_FIN": "classi_fin",
        # updated on 12-2024
        "DT_CHIK_S1": "dt_chik_s1",
        "DT_CHIK_S2": "dt_chik_s2",
        "DT_PRNT": "dt_prnt",
        "RES_CHIKS1": "res_chiks1",
        "RES_CHIKS2": "res_chiks2",
        "RESUL_PRNT": "resul_prnt",
        "DT_SORO": "dt_soro",
        "RESUL_SORO": "resul_soro",
        "DT_NS1": "dt_ns1",
        "RESUL_NS1": "resul_ns1",
        "DT_VIRAL": "dt_viral",
        "RESUL_VI_N": "resul_vi_n",
        "DT_PCR": "dt_pcr",
        "SOROTIPO": "sorotipo",
        "ID_DISTRIT": "id_distrit",
        "ID_BAIRRO": "id_bairro",
        "NM_BAIRRO": "nm_bairro",
        "ID_UNIDADE": "id_unidade",
    }

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
    date_formats = models.JSONField(
        null=False,
        default=dict,
        help_text="A dict with {'DT_COLUMN': 'date format'}"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.upload.filename}"

    def _final_basename(self):
        filename = str(Path(self.upload.filename).with_suffix(""))
        disease = {"A90": "DENG", "A92.0": "CHIK", "A928": "ZIKA"}
        uf = self.uf if self.uf else "BR"
        epiweek = Week.fromdate(self.uploaded_at)
        return (
            "_".join([str(epiweek), disease[self.cid10], uf]) + "-" + filename
        )

    def delete(self, *args, **kwargs):
        file = Path(self.upload.file.path)

        if not file.exists():
            super(SINANUpload, self).delete(*args, **kwargs)
            return

        if self.status and self.status.status == 0:
            raise RuntimeError(f"{file} is still being processed")

        if self.status and self.status.status == 1:
            raise RuntimeError(
                f"{file} is attached with this upload, delete the file first"
            )

        if not self.status or self.status.status == 2:
            file.unlink()

        super(SINANUpload, self).delete(*args, **kwargs)

    class Meta:
        app_label = "upload"


class SINANUploadFatalError(Exception):
    def __init__(self, log_status: SINANUploadLogStatus, error_message: str):
        try:
            log_status.fatal(error_message)
        except ValueError:
            pass
        super().__init__(error_message)
