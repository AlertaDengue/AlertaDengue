from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO

from django.core.management import call_command
import pytest

from ingestion.models import (
    RollbackStatus,
    Run,
    RunRollback,
    RunStatus,
    SinanStage,
)
from ingestion.retention import (
    execute_stage_cleanup,
    get_cleanup_candidates,
    preview_stage_cleanup,
)

NOW = datetime(2026, 2, 1, 12, tzinfo=UTC)


def _run(
    *,
    year: int = 2025,
    week: int = 1,
    days_old: int = 60,
    status: str = RunStatus.COMPLETED,
    uf: str = "RJ",
    disease: str = "A90",
) -> Run:
    """Create a run with deterministic delivery and created-at metadata."""
    run = Run.objects.create(
        status=status,
        uf=uf,
        disease=disease,
        source_format="csv",
        delivery_year=year,
        delivery_week=week,
        source_path=f"test/{Run.objects.count()}",
        filename="test.csv",
        sha256=f"{Run.objects.count():064d}",
        size_bytes=1,
    )
    Run.objects.filter(pk=run.pk).update(
        created_at=NOW - timedelta(days=days_old)
    )
    run.refresh_from_db()
    return run


def _stage(run: Run, rownum: int = 1) -> None:
    """Create one lightweight stage row for a run."""
    SinanStage.objects.create(
        run=run,
        chunk_id=0,
        source_rownum=rownum,
    )


def _candidate_ids(**kwargs: object) -> set[object]:
    return set(
        get_cleanup_candidates(now=NOW, **kwargs).values_list("pk", flat=True)
    )


@pytest.mark.django_db
def test_age_protects_recent_completed_runs() -> None:
    recent = _run(days_old=29, week=1)
    old = _run(days_old=31, week=2)

    assert old.pk in _candidate_ids(keep_epiweeks=0)
    assert recent.pk not in _candidate_ids(keep_epiweeks=0)


@pytest.mark.django_db
def test_epiweek_protection_keeps_latest_four_distinct_weeks() -> None:
    oldest = _run(year=2025, week=50)
    protected = [_run(year=2025, week=week) for week in range(51, 55)]
    same_week = _run(year=2025, week=54)

    candidates = _candidate_ids(retention_days=0)

    assert candidates == {oldest.pk}
    assert all(run.pk not in candidates for run in [*protected, same_week])


@pytest.mark.django_db
def test_epiweek_protection_is_partitioned_by_uf_and_disease() -> None:
    rj_old = _run(week=1, uf="RJ", disease="A90")
    sp_old = _run(week=1, uf="SP", disease="A90")
    chik_old = _run(week=1, uf="RJ", disease="A92")
    for week in range(2, 6):
        _run(week=week, uf="RJ", disease="A90")

    candidates = _candidate_ids(retention_days=0)

    assert rj_old.pk in candidates
    assert sp_old.pk not in candidates
    assert chik_old.pk not in candidates


@pytest.mark.django_db
def test_epiweek_ordering_crosses_year_boundary() -> None:
    weeks = [(2025, 52), (2026, 1), (2026, 2), (2026, 3), (2026, 4)]
    runs = [_run(year=year, week=week) for year, week in weeks]

    candidates = _candidate_ids(retention_days=0)

    assert candidates == {runs[0].pk}


@pytest.mark.django_db
def test_rollback_references_protect_current_restore_and_failed_records() -> (
    None
):
    current = _run(week=1)
    restore = _run(week=2)
    failed_current = _run(week=3)
    failed_restore = _run(week=4)
    eligible = _run(week=5)
    RunRollback.objects.create(current_run=current, restore_run=restore)
    RunRollback.objects.create(
        current_run=failed_current,
        restore_run=failed_restore,
        status=RollbackStatus.FAILED,
    )

    candidates = _candidate_ids(retention_days=0, keep_epiweeks=0)

    assert candidates == {eligible.pk}


@pytest.mark.django_db
def test_non_completed_runs_are_never_cleanup_candidates() -> None:
    run = _run(status=RunStatus.FAILED)
    _stage(run)

    assert run.pk not in _candidate_ids(retention_days=0, keep_epiweeks=0)
    assert SinanStage.objects.filter(run=run).exists()


@pytest.mark.django_db
def test_cleanup_deletes_only_eligible_stage_rows_and_keeps_audit_history() -> (
    None
):
    eligible = _run(week=1)
    protected = _run(days_old=1, week=2)
    restore = _run(week=3)
    current = _run(week=4)
    _stage(eligible)
    _stage(protected)
    _stage(restore)
    _stage(current)
    rollback = RunRollback.objects.create(
        current_run=current,
        restore_run=restore,
    )

    result = execute_stage_cleanup(keep_epiweeks=0, now=NOW)

    assert (result.deleted_runs_count, result.deleted_stage_rows) == (1, 1)
    assert not SinanStage.objects.filter(run=eligible).exists()
    assert (
        SinanStage.objects.filter(
            run__in=[protected, restore, current]
        ).count()
        == 3
    )
    assert Run.objects.filter(pk=eligible.pk).exists()
    assert RunRollback.objects.filter(pk=rollback.pk).exists()


@pytest.mark.django_db
def test_dry_run_reports_candidates_without_deleting_rows() -> None:
    eligible = _run(week=1)
    _stage(eligible)
    output = StringIO()

    call_command(
        "cleanup_ingestion_stage",
        "--dry-run",
        "--keep-epiweeks=0",
        stdout=output,
    )

    assert str(eligible.pk) in output.getvalue()
    assert "Candidate SinanStage rows: 1" in output.getvalue()
    assert SinanStage.objects.filter(run=eligible).exists()


@pytest.mark.django_db
def test_execution_reports_expected_counts_and_is_idempotent() -> None:
    eligible = _run(week=1)
    _stage(eligible, 1)
    _stage(eligible, 2)

    first = execute_stage_cleanup(keep_epiweeks=0, now=NOW)
    second = execute_stage_cleanup(keep_epiweeks=0, now=NOW)

    assert (first.deleted_runs_count, first.deleted_stage_rows) == (1, 2)
    assert (second.deleted_runs_count, second.deleted_stage_rows) == (0, 0)


@pytest.mark.django_db
def test_combined_age_epiweek_and_rollback_protections() -> None:
    for week in range(1, 5):
        _run(year=2026, week=week)
    epiweek_run = Run.objects.get(delivery_year=2026, delivery_week=4)
    current = _run(year=2025, week=1)
    restore = _run(year=2025, week=2)
    old = _run(year=2025, week=3)
    RunRollback.objects.create(current_run=current, restore_run=restore)

    candidates = _candidate_ids(retention_days=30)

    assert epiweek_run.pk not in candidates
    assert current.pk not in candidates
    assert restore.pk not in candidates
    assert old.pk in candidates


@pytest.mark.django_db
def test_preview_counts_candidate_stage_rows() -> None:
    eligible = _run(week=1)
    _stage(eligible, 1)
    _stage(eligible, 2)

    preview = preview_stage_cleanup(keep_epiweeks=0, now=NOW)

    assert (preview.candidate_runs, preview.candidate_stage_rows) == (1, 2)
