from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from ingestion.management.commands import ingestion_enqueue_sinan as cmd
from ingestion.models import Run, RunStatus


@dataclass(frozen=True, slots=True)
class _AsyncResult:
    """
    Minimal Celery AsyncResult-like object.

    Attributes
    ----------
    id
        Task id.
    """

    id: str


class _DelayStub:
    """
    Stub for Celery task object exposing .delay().
    """

    def __init__(self) -> None:
        self.calls: list[str] = []

    def delay(self, run_id: str) -> _AsyncResult:
        """
        Record the call and return a fake task id.

        Parameters
        ----------
        run_id
            Run id as string.

        Returns
        -------
        _AsyncResult
            Result-like object.
        """
        self.calls.append(run_id)
        return _AsyncResult(id="task-1")


@pytest.mark.django_db
def test_enqueue_creates_run_and_sets_task_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    First enqueue creates a Run and stores celery_task_id.
    """

    Run.objects.all().delete()

    fpath = tmp_path / "file.csv"
    fpath.write_text("CID10;SEM_NOT\nA90;202605\n", encoding="utf-8")

    stub = _DelayStub()
    monkeypatch.setattr(cmd, "enqueue_sinan_run", stub)

    call_command(
        "ingestion_enqueue_sinan",
        str(fpath),
        "--uf",
        "ES",
        "--disease",
        "A90",
        "--year",
        "2026",
        "--week",
        "5",
    )

    file_sha = cmd._sha256_file(fpath)
    run = Run.objects.get(sha256=file_sha)
    assert run.status == RunStatus.QUEUED
    assert run.celery_task_id == "task-1"
    assert len(stub.calls) == 1


@pytest.mark.django_db
def test_enqueue_existing_run_no_requeue_does_not_delay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Second enqueue with same sha does not call .delay without --requeue.
    """

    Run.objects.all().delete()

    fpath = tmp_path / "file.csv"
    fpath.write_text("CID10;SEM_NOT\nA90;202605\n", encoding="utf-8")

    stub = _DelayStub()
    monkeypatch.setattr(cmd, "enqueue_sinan_run", stub)

    call_command(
        "ingestion_enqueue_sinan",
        str(fpath),
        "--uf",
        "ES",
        "--disease",
        "A90",
        "--year",
        "2026",
        "--week",
        "5",
    )
    call_command(
        "ingestion_enqueue_sinan",
        str(fpath),
        "--uf",
        "ES",
        "--disease",
        "A90",
        "--year",
        "2026",
        "--week",
        "5",
    )

    assert len(stub.calls) == 1


@pytest.mark.django_db
def test_enqueue_requeue_calls_delay_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    With --requeue, an existing run enqueues again.
    """

    Run.objects.all().delete()

    fpath = tmp_path / "file.csv"
    fpath.write_text("CID10;SEM_NOT\nA90;202605\n", encoding="utf-8")

    stub = _DelayStub()
    monkeypatch.setattr(cmd, "enqueue_sinan_run", stub)

    call_command(
        "ingestion_enqueue_sinan",
        str(fpath),
        "--uf",
        "ES",
        "--disease",
        "A90",
        "--year",
        "2026",
        "--week",
        "5",
    )
    call_command(
        "ingestion_enqueue_sinan",
        str(fpath),
        "--uf",
        "ES",
        "--disease",
        "A90",
        "--year",
        "2026",
        "--week",
        "5",
        "--requeue",
    )

    assert len(stub.calls) == 2


@pytest.mark.django_db
def test_enqueue_validates_week_range(tmp_path: Path) -> None:
    """
    Week outside 1..53 raises CommandError.
    """

    Run.objects.all().delete()
    fpath = tmp_path / "file.csv"
    fpath.write_text("CID10;SEM_NOT\nA90;202605\n", encoding="utf-8")

    with pytest.raises(CommandError):
        call_command(
            "ingestion_enqueue_sinan",
            str(fpath),
            "--uf",
            "ES",
            "--disease",
            "A90",
            "--year",
            "2026",
            "--week",
            "54",
        )
