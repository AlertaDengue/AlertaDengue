from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS ingestion;",
            reverse_sql="DROP SCHEMA IF EXISTS ingestion CASCADE;",
        ),
        migrations.CreateModel(
            name="Run",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        editable=False,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("detected", "Detected"),
                            ("queued", "Queued"),
                            ("staging", "Staging"),
                            ("staged", "Staged"),
                            ("merging", "Merging"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="detected",
                        max_length=16,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("uf", models.CharField(max_length=2)),
                (
                    "source_format",
                    models.CharField(
                        choices=[
                            ("dbf", "DBF"),
                            ("csv", "CSV"),
                            ("parquet", "Parquet"),
                        ],
                        max_length=16,
                    ),
                ),
                ("disease", models.CharField(max_length=16)),
                ("delivery_year", models.SmallIntegerField()),
                ("delivery_week", models.SmallIntegerField()),
                ("delivery_se", models.IntegerField(editable=False)),
                ("source_path", models.TextField()),
                ("filename", models.TextField()),
                ("sha256", models.CharField(max_length=64, unique=True)),
                ("size_bytes", models.BigIntegerField()),
                ("mtime", models.DateTimeField(blank=True, null=True)),
                ("celery_task_id", models.TextField(blank=True, null=True)),
                ("worker_hostname", models.TextField(blank=True, null=True)),
                ("rows_read", models.BigIntegerField(default=0)),
                ("rows_parsed", models.BigIntegerField(default=0)),
                ("rows_loaded", models.BigIntegerField(default=0)),
                ("rows_failed", models.BigIntegerField(default=0)),
                ("metadata", models.JSONField(default=dict)),
                ("errors", models.JSONField(default=list)),
            ],
            options={
                "db_table": '"ingestion"."run"',
            },
        ),
        migrations.CreateModel(
            name="SinanStage",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("chunk_id", models.IntegerField(default=0)),
                ("source_rownum", models.BigIntegerField()),
                ("dt_notific", models.DateField(blank=True, null=True)),
                ("se_notif", models.IntegerField(blank=True, null=True)),
                ("ano_notif", models.IntegerField(blank=True, null=True)),
                ("dt_sin_pri", models.DateField(blank=True, null=True)),
                ("se_sin_pri", models.IntegerField(blank=True, null=True)),
                ("dt_digita", models.DateField(blank=True, null=True)),
                (
                    "municipio_geocodigo",
                    models.IntegerField(blank=True, null=True),
                ),
                ("nu_notific", models.IntegerField(blank=True, null=True)),
                (
                    "cid10_codigo",
                    models.CharField(blank=True, max_length=5, null=True),
                ),
                ("dt_nasc", models.DateField(blank=True, null=True)),
                (
                    "cs_sexo",
                    models.CharField(blank=True, max_length=1, null=True),
                ),
                ("nu_idade_n", models.IntegerField(blank=True, null=True)),
                ("resul_pcr", models.FloatField(blank=True, null=True)),
                ("criterio", models.FloatField(blank=True, null=True)),
                ("classi_fin", models.FloatField(blank=True, null=True)),
                ("dt_chik_s1", models.DateField(blank=True, null=True)),
                ("dt_chik_s2", models.DateField(blank=True, null=True)),
                ("dt_prnt", models.DateField(blank=True, null=True)),
                (
                    "res_chiks1",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "res_chiks2",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "resul_prnt",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("dt_soro", models.DateField(blank=True, null=True)),
                (
                    "resul_soro",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("dt_ns1", models.DateField(blank=True, null=True)),
                (
                    "resul_ns1",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("dt_viral", models.DateField(blank=True, null=True)),
                (
                    "resul_vi_n",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("dt_pcr", models.DateField(blank=True, null=True)),
                (
                    "sorotipo",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("id_distrit", models.FloatField(blank=True, null=True)),
                ("id_bairro", models.FloatField(blank=True, null=True)),
                (
                    "nm_bairro",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("id_unidade", models.FloatField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ingestion.run",
                    ),
                ),
            ],
            options={
                "db_table": '"ingestion"."sinan_stage"',
            },
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS ix_ing_run_scope "
                "ON ingestion.run (uf, disease, delivery_se DESC);"
            ),
            reverse_sql="DROP INDEX IF EXISTS ix_ing_run_scope;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS ix_ing_run_status_created "
                "ON ingestion.run (status, created_at DESC);"
            ),
            reverse_sql="DROP INDEX IF EXISTS ix_ing_run_status_created;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS ix_ing_sinan_stage_run "
                "ON ingestion.sinan_stage (run_id);"
            ),
            reverse_sql="DROP INDEX IF EXISTS ix_ing_sinan_stage_run;",
        ),
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS ix_ing_sinan_stage_keys "
                "ON ingestion.sinan_stage "
                "(run_id, cid10_codigo, nu_notific, municipio_geocodigo);"
            ),
            reverse_sql="DROP INDEX IF EXISTS ix_ing_sinan_stage_keys;",
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE ingestion.sinan_stage "
                "ADD CONSTRAINT ux_ing_sinan_stage_row "
                "UNIQUE (run_id, chunk_id, source_rownum);"
            ),
            reverse_sql=(
                "ALTER TABLE ingestion.sinan_stage "
                "DROP CONSTRAINT IF EXISTS ux_ing_sinan_stage_row;"
            ),
        ),
    ]
