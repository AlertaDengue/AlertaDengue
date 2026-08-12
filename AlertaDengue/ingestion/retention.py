"""Retention policy for retained SINAN staging snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ingestion.models import Run, RunRollback, RunStatus, SinanStage


@dataclass(frozen=True)
class StageCleanupPreview:
    """Counts produced while evaluating the stage cleanup policy."""

    evaluated_runs: int
    protected_recent: int
    protected_epiweeks: int
    protected_epiweek_runs: int
    protected_rollbacks: int
    candidate_runs: int
    candidate_stage_rows: int


@dataclass(frozen=True)
class StageCleanupResult:
    """Counts produced by a completed stage cleanup execution."""

    deleted_runs_count: int
    deleted_stage_rows: int


class StageCleanupExecutionError(RuntimeError):
    """Report completed per-run deletions when a later deletion fails."""

    def __init__(self, deleted_runs_count: int, deleted_stage_rows: int):
        self.deleted_runs_count = deleted_runs_count
        self.deleted_stage_rows = deleted_stage_rows
        super().__init__("SINAN stage cleanup stopped before completion.")


@dataclass(frozen=True)
class _ProtectedRuns:
    """Run identifiers protected by each retention policy rule."""

    recent_ids: set[UUID]
    epiweek_ids: set[UUID]
    rollback_ids: set[UUID]
    epiweek_count: int

    @property
    def all_ids(self) -> set[UUID]:
        """Return the union of all protected run identifiers."""
        return self.recent_ids | self.epiweek_ids | self.rollback_ids


def _completed_runs() -> QuerySet[Run]:
    """Return the only run status eligible for v1 cleanup."""
    return Run.objects.filter(status=RunStatus.COMPLETED)


def _latest_epiweek_ids(
    runs: Iterable[tuple[UUID, str, str, int]],
    keep_epiweeks: int,
) -> tuple[set[UUID], int]:
    """Return run IDs from the newest distinct delivery epiweeks per scope."""
    by_scope: dict[tuple[str, str], dict[int, set[UUID]]] = {}
    for run_id, uf, disease, delivery_se in runs:
        scope = (uf, disease)
        by_scope.setdefault(scope, {}).setdefault(delivery_se, set()).add(
            run_id
        )

    protected_ids: set[UUID] = set()
    protected_epiweeks = 0
    for epiweeks in by_scope.values():
        latest = sorted(epiweeks, reverse=True)[:keep_epiweeks]
        protected_epiweeks += len(latest)
        for epiweek in latest:
            protected_ids.update(epiweeks[epiweek])
    return protected_ids, protected_epiweeks


def get_protected_run_ids(
    *,
    retention_days: int = 30,
    keep_epiweeks: int = 4,
    now: datetime | None = None,
) -> _ProtectedRuns:
    """Return completed runs protected from stage cleanup by policy rules."""
    if retention_days < 0:
        raise ValueError("retention_days must be zero or greater.")
    if keep_epiweeks < 0:
        raise ValueError("keep_epiweeks must be zero or greater.")

    now = now or timezone.now()
    completed = _completed_runs()
    recent_ids = set(
        completed.filter(
            created_at__gte=now - timedelta(days=retention_days)
        ).values_list("pk", flat=True)
    )
    epiweek_ids, epiweek_count = _latest_epiweek_ids(
        completed.values_list("pk", "uf", "disease", "delivery_se"),
        keep_epiweeks,
    )
    rollback_reference_ids = set(
        RunRollback.objects.values_list("current_run_id", flat=True)
    ) | set(RunRollback.objects.values_list("restore_run_id", flat=True))
    rollback_ids = set(
        completed.filter(pk__in=rollback_reference_ids).values_list(
            "pk", flat=True
        )
    )
    return _ProtectedRuns(
        recent_ids=recent_ids,
        epiweek_ids=epiweek_ids,
        rollback_ids=rollback_ids,
        epiweek_count=epiweek_count,
    )


def get_cleanup_candidates(
    *,
    retention_days: int = 30,
    keep_epiweeks: int = 4,
    now: datetime | None = None,
) -> QuerySet[Run]:
    """Return completed runs whose stage rows may be safely removed."""
    protected = get_protected_run_ids(
        retention_days=retention_days,
        keep_epiweeks=keep_epiweeks,
        now=now,
    )
    return _completed_runs().exclude(pk__in=protected.all_ids)


def preview_stage_cleanup(
    *,
    retention_days: int = 30,
    keep_epiweeks: int = 4,
    now: datetime | None = None,
) -> StageCleanupPreview:
    """Evaluate the cleanup policy without deleting any staging rows."""
    now = now or timezone.now()
    protected = get_protected_run_ids(
        retention_days=retention_days,
        keep_epiweeks=keep_epiweeks,
        now=now,
    )
    candidates = _completed_runs().exclude(pk__in=protected.all_ids)
    return StageCleanupPreview(
        evaluated_runs=_completed_runs().count(),
        protected_recent=len(protected.recent_ids),
        protected_epiweeks=protected.epiweek_count,
        protected_epiweek_runs=len(protected.epiweek_ids),
        protected_rollbacks=len(protected.rollback_ids),
        candidate_runs=candidates.count(),
        candidate_stage_rows=SinanStage.objects.filter(
            run__in=candidates
        ).count(),
    )


def execute_stage_cleanup(
    *,
    retention_days: int = 30,
    keep_epiweeks: int = 4,
    now: datetime | None = None,
) -> StageCleanupResult:
    """Re-evaluate policy and delete eligible stage rows one run at a time."""
    candidates = get_cleanup_candidates(
        retention_days=retention_days,
        keep_epiweeks=keep_epiweeks,
        now=now,
    )
    deleted_runs_count = 0
    deleted_stage_rows = 0
    for run_id in candidates.values_list("pk", flat=True).iterator():
        try:
            with transaction.atomic():
                deleted_rows, _ = SinanStage.objects.filter(
                    run_id=run_id
                ).delete()
        except Exception as exc:
            raise StageCleanupExecutionError(
                deleted_runs_count,
                deleted_stage_rows,
            ) from exc
        if deleted_rows:
            deleted_runs_count += 1
            deleted_stage_rows += deleted_rows
    return StageCleanupResult(
        deleted_runs_count=deleted_runs_count,
        deleted_stage_rows=deleted_stage_rows,
    )
