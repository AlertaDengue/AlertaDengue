from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone
from ingestion.models import Run, RunStatus, SourceFormat
from ingestion.schemas import RunError
from ingestion.tasks import enqueue_sinan_run


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA256 for a file.

    Parameters
    ----------
    path
        File path to hash.
    chunk_size
        Read chunk size in bytes.

    Returns
    -------
    str
        Hex-encoded SHA256 digest.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


class Command(BaseCommand):
    help = "Create/reuse a SINAN ingestion Run and enqueue Celery processing."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("source_path", type=str)

        parser.add_argument("--uf", required=True, type=str)
        parser.add_argument("--disease", required=True, type=str)
        parser.add_argument("--year", required=True, type=int)
        parser.add_argument("--week", required=True, type=int)

        parser.add_argument(
            "--requeue",
            action="store_true",
            help="Enqueue the task even if the run already exists.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        source_path = Path(options["source_path"]).expanduser()
        if not source_path.exists():
            raise CommandError(f"File not found: {source_path}")

        uf = str(options["uf"]).upper().strip()
        disease = str(options["disease"]).strip()
        year = int(options["year"])
        week = int(options["week"])
        requeue = bool(options["requeue"])

        if len(uf) != 2:
            raise CommandError("--uf must have 2 letters (e.g. ES).")

        if week < 1 or week > 53:
            raise CommandError("--week must be between 1 and 53.")

        suffix = source_path.suffix.lower().lstrip(".")
        if suffix not in {
            SourceFormat.DBF,
            SourceFormat.CSV,
            SourceFormat.PARQUET,
        }:
            raise CommandError(f"Unsupported file type: {source_path.suffix}")

        file_sha256 = _sha256_file(source_path)
        stat = source_path.stat()
        mtime = timezone.make_aware(
            timezone.datetime.fromtimestamp(stat.st_mtime),
            timezone.get_current_timezone(),
        )

        defaults = {
            "uf": uf,
            "disease": disease,
            "delivery_year": year,
            "delivery_week": week,
            "source_format": suffix,
            "source_path": str(source_path),
            "filename": source_path.name,
            "sha256": file_sha256,
            "size_bytes": int(stat.st_size),
            "mtime": mtime,
            "status": RunStatus.QUEUED,
        }

        try:
            with transaction.atomic():
                run, created = Run.objects.get_or_create(
                    sha256=file_sha256,
                    defaults=defaults,
                )
        except IntegrityError:
            run = Run.objects.get(sha256=file_sha256)
            created = False

        if not created:
            msg = (
                f"Run already exists for sha256={file_sha256} "
                f"(run_id={run.id})."
            )
            self.stdout.write(self.style.WARNING(msg))

            if not requeue:
                return

            if run.status in {RunStatus.COMPLETED}:
                run.status = RunStatus.QUEUED
                run.save(update_fields=["status", "updated_at"])

        try:
            async_result = enqueue_sinan_run.delay(str(run.id))
        except Exception as exc:
            run.append_error(
                RunError(
                    step="enqueue",
                    code=exc.__class__.__name__,
                    message=str(exc),
                ).model_dump()
            )

            run.status = RunStatus.FAILED
            run.finished_at = timezone.now()
            run.save(update_fields=["status", "finished_at", "updated_at"])

            raise CommandError(
                "Could not enqueue Celery task (broker unreachable?). "
                f"run_id={run.id} error={exc}"
            )

        run.celery_task_id = str(async_result.id)
        run.status = RunStatus.QUEUED
        run.save(update_fields=["celery_task_id", "status", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Enqueued run_id={run.id} task_id={async_result.id}"
            )
        )
