"""Clean expired SINAN staging snapshots without removing run history."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from ingestion.retention import (
    StageCleanupExecutionError,
    StageCleanupPreview,
    execute_stage_cleanup,
    get_cleanup_candidates,
    preview_stage_cleanup,
)


class Command(BaseCommand):
    """Run the safe SINAN stage retention policy."""

    help = "Preview or remove expired SINAN staging rows."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show eligible runs and row counts without deleting data.",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=30,
            help="Keep completed runs created in this many recent days.",
        )
        parser.add_argument(
            "--keep-epiweeks",
            type=int,
            default=4,
            help="Keep this many latest distinct epiweeks per UF and disease.",
        )

    def _write_preview(
        self, preview: StageCleanupPreview, dry_run: bool
    ) -> None:
        self.stdout.write(f"Dry run: {'yes' if dry_run else 'no'}")
        self.stdout.write(f"Runs evaluated: {preview.evaluated_runs}")
        self.stdout.write(
            f"Runs protected by recent age: {preview.protected_recent}"
        )
        self.stdout.write(f"Epiweeks protected: {preview.protected_epiweeks}")
        self.stdout.write(
            f"Runs protected by epiweek: {preview.protected_epiweek_runs}"
        )
        self.stdout.write(
            "Runs protected by rollback history: "
            f"{preview.protected_rollbacks}"
        )
        self.stdout.write(f"Candidate runs: {preview.candidate_runs}")
        self.stdout.write(
            f"Candidate SinanStage rows: {preview.candidate_stage_rows}"
        )

    def _write_candidates(
        self,
        *,
        retention_days: int,
        keep_epiweeks: int,
        now: datetime,
    ) -> None:
        candidates = (
            get_cleanup_candidates(
                retention_days=retention_days,
                keep_epiweeks=keep_epiweeks,
                now=now,
            )
            .annotate(stage_rows=Count("sinanstage"))
            .order_by("created_at")
        )
        self.stdout.write("Candidate runs:")
        for run in candidates.iterator():
            self.stdout.write(
                "  "
                f"{run.pk} {run.uf} {run.disease} "
                f"{run.delivery_year}-W{run.delivery_week:02d} "
                f"{run.created_at.isoformat()} stage_rows={run.stage_rows}"
            )
        if not candidates.exists():
            self.stdout.write("  none")

    def handle(self, *args: Any, **options: Any) -> None:
        retention_days = int(options["retention_days"])
        keep_epiweeks = int(options["keep_epiweeks"])
        dry_run = bool(options["dry_run"])
        if retention_days < 0 or keep_epiweeks < 0:
            raise CommandError("Retention values must be zero or greater.")
        now = timezone.now()
        preview = preview_stage_cleanup(
            retention_days=retention_days,
            keep_epiweeks=keep_epiweeks,
            now=now,
        )
        self._write_preview(preview, dry_run)
        self._write_candidates(
            retention_days=retention_days,
            keep_epiweeks=keep_epiweeks,
            now=now,
        )
        if dry_run:
            return

        try:
            result = execute_stage_cleanup(
                retention_days=retention_days,
                keep_epiweeks=keep_epiweeks,
                now=timezone.now(),
            )
        except StageCleanupExecutionError as exc:
            self.stdout.write(
                f"Deleted SinanStage rows: {exc.deleted_stage_rows}"
            )
            self.stdout.write(
                f"Runs with deleted stage rows: {exc.deleted_runs_count}"
            )
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"Deleted SinanStage rows: {result.deleted_stage_rows}"
        )
        self.stdout.write(
            f"Runs with deleted stage rows: {result.deleted_runs_count}"
        )
