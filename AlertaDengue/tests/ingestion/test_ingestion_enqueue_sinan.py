from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from ingestion.management.commands import ingestion_enqueue_sinan as cmd
from ingestion.models import Run, RunStatus


def _write_unique_csv(path: Path, *, token: str) -> None:
    """
    Write a CSV whose sha256 is unique per test.

    Parameters
    ----------
    path
        Output file path.
    token
        Token included in file content to avoid checksum collisions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "CID10;SEM_NOT\n" "A90;202605\n" f"{token}\n",
        encoding="utf-8",
    )


def _ensure_run_absent_for_file(path: Path) -> None:
    """
    Remove any existing Run row for the file sha256.

    This makes the test idempotent even if CI reuses a persistent database.

    Parameters
    ----------
    path
        File whose sha256 is used to match Runs.
    """
    sha256 = cmd._sha256_file(path)
    Run.objects.filter(sha256=sha256).delete()


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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    First enqueue creates a Run and stores celery_task_id.
    """
    fpath = tmp_path / "file.csv"
    _write_unique_csv(fpath, token=f"t1:{tmp_path}")
    _ensure_run_absent_for_file(fpath)

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
    fpath = tmp_path / "file.csv"
    _write_unique_csv(fpath, token=f"t2:{tmp_path}")
    _ensure_run_absent_for_file(fpath)

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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    With --requeue, an existing run enqueues again.
    """
    fpath = tmp_path / "file.csv"
    _write_unique_csv(fpath, token=f"t3:{tmp_path}")
    _ensure_run_absent_for_file(fpath)

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
    fpath = tmp_path / "file.csv"
    _write_unique_csv(fpath, token=f"t4:{tmp_path}")
    _ensure_run_absent_for_file(fpath)

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
