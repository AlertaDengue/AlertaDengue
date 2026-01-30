from __future__ import annotations

import uuid
from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from ingestion.schemas import RunError, RunMetadata


class RunStatus(models.TextChoices):
    DETECTED = "detected", "Detected"
    QUEUED = "queued", "Queued"
    STAGING = "staging", "Staging"
    STAGED = "staged", "Staged"
    MERGING = "merging", "Merging"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class SourceFormat(models.TextChoices):
    DBF = "dbf", "DBF"
    CSV = "csv", "CSV"
    PARQUET = "parquet", "Parquet"


class Run(models.Model):
    """
    Ingestion run control record.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=RunStatus.choices,
        default=RunStatus.DETECTED,
    )
    attempts = models.PositiveIntegerField(default=0)

    uf = models.CharField(max_length=2)
    source_format = models.CharField(
        max_length=16, choices=SourceFormat.choices
    )
    disease = models.CharField(max_length=16)

    delivery_year = models.SmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    delivery_week = models.SmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(53)]
    )
    delivery_se = models.IntegerField(editable=False)

    source_path = models.TextField()
    filename = models.TextField()

    sha256 = models.CharField(max_length=64, unique=True)
    size_bytes = models.BigIntegerField(validators=[MinValueValidator(0)])
    mtime = models.DateTimeField(null=True, blank=True)

    celery_task_id = models.TextField(null=True, blank=True)
    worker_hostname = models.TextField(null=True, blank=True)

    rows_read = models.BigIntegerField(default=0)
    rows_parsed = models.BigIntegerField(default=0)
    rows_loaded = models.BigIntegerField(default=0)
    rows_failed = models.BigIntegerField(default=0)

    metadata = models.JSONField(default=dict)
    errors = models.JSONField(default=list)

    class Meta:
        db_table = '"ingestion"."run"'
        indexes = [
            models.Index(
                fields=["uf", "disease", "-delivery_se"],
                name="ix_ing_run_scope",
            ),
            models.Index(
                fields=["status", "-created_at"],
                name="ix_ing_run_status_created",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.delivery_se = int(self.delivery_year) * 100 + int(
            self.delivery_week
        )
        super().save(*args, **kwargs)

    def set_metadata(self, value: dict[str, Any]) -> None:
        meta = RunMetadata.model_validate(value)
        self.metadata = meta.model_dump(mode="json")
        self.save(update_fields=["metadata", "updated_at"])

    def append_error(self, value: dict[str, Any]) -> None:
        err = RunError.model_validate(value).model_dump(mode="json")
        self.errors = [*self.errors, err]
        self.save(update_fields=["errors", "updated_at"])


class SinanStage(models.Model):
    """
    Staging table for SINAN rows (canonical Notificacao column names).
    """

    id = models.BigAutoField(primary_key=True)

    run = models.ForeignKey(Run, on_delete=models.CASCADE)
    chunk_id = models.IntegerField(default=0)
    source_rownum = models.BigIntegerField()

    dt_notific = models.DateField(null=True, blank=True)
    se_notif = models.IntegerField(null=True, blank=True)
    ano_notif = models.IntegerField(null=True, blank=True)

    dt_sin_pri = models.DateField(null=True, blank=True)
    se_sin_pri = models.IntegerField(null=True, blank=True)

    dt_digita = models.DateField(null=True, blank=True)

    municipio_geocodigo = models.IntegerField(null=True, blank=True)
    nu_notific = models.IntegerField(null=True, blank=True)
    cid10_codigo = models.CharField(max_length=5, null=True, blank=True)

    dt_nasc = models.DateField(null=True, blank=True)
    cs_sexo = models.CharField(max_length=1, null=True, blank=True)
    nu_idade_n = models.IntegerField(null=True, blank=True)

    resul_pcr = models.FloatField(null=True, blank=True)
    criterio = models.FloatField(null=True, blank=True)
    classi_fin = models.FloatField(null=True, blank=True)

    dt_chik_s1 = models.DateField(null=True, blank=True)
    dt_chik_s2 = models.DateField(null=True, blank=True)
    dt_prnt = models.DateField(null=True, blank=True)

    res_chiks1 = models.CharField(max_length=255, null=True, blank=True)
    res_chiks2 = models.CharField(max_length=255, null=True, blank=True)
    resul_prnt = models.CharField(max_length=255, null=True, blank=True)

    dt_soro = models.DateField(null=True, blank=True)
    resul_soro = models.CharField(max_length=255, null=True, blank=True)

    dt_ns1 = models.DateField(null=True, blank=True)
    resul_ns1 = models.CharField(max_length=255, null=True, blank=True)

    dt_viral = models.DateField(null=True, blank=True)
    resul_vi_n = models.CharField(max_length=255, null=True, blank=True)

    dt_pcr = models.DateField(null=True, blank=True)
    sorotipo = models.CharField(max_length=255, null=True, blank=True)

    id_distrit = models.FloatField(null=True, blank=True)
    id_bairro = models.FloatField(null=True, blank=True)
    nm_bairro = models.CharField(max_length=255, null=True, blank=True)
    id_unidade = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '"ingestion"."sinan_stage"'
        constraints = [
            models.UniqueConstraint(
                fields=["run", "chunk_id", "source_rownum"],
                name="ux_ing_sinan_stage_row",
            ),
        ]
        indexes = [
            models.Index(fields=["run"], name="ix_ing_sinan_stage_run"),
            models.Index(
                fields=[
                    "run",
                    "cid10_codigo",
                    "nu_notific",
                    "municipio_geocodigo",
                ],
                name="ix_ing_sinan_stage_keys",
            ),
        ]
