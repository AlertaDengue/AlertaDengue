from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.management import call_command
from ingestion.management.commands import ingestion_enqueue_manifest as man


class _CallCapture:
    """
    Capture calls to call_command("ingestion_enqueue_sinan", ...).
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def __call__(self, name: str, *args: str) -> None:
        """
        Capture invocations.

        Parameters
        ----------
        name
            Command name.
        args
            Positional args passed to call_command.
        """
        self.calls.append((name, tuple(args)))


@pytest.mark.django_db
def test_manifest_sort_order_and_arg_building(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Enqueue order is ES first; within each country, earlier weeks first.
    """
    manifest_path = tmp_path / "manifest.json"
    entries = [
        {
            "dest": "/x/br.csv",
            "country": "br",
            "disease": "A90",
            "year": 2026,
            "week": 5,
            "sem_not_max": 202605,
            "uf": "BR",
        },
        {
            "dest": "/x/es.csv",
            "country": "es",
            "disease": "A90",
            "year": 2026,
            "week": 4,
            "sem_not_max": 202604,
            "uf": "ES",
        },
    ]
    manifest_path.write_text(
        json.dumps(entries, ensure_ascii=False),
        encoding="utf-8",
    )

    capture = _CallCapture()
    monkeypatch.setattr(man, "call_command", capture)

    call_command(
        "ingestion_enqueue_manifest",
        "--manifest",
        str(manifest_path),
        "--host-base",
        "/host",
        "--worker-base",
        "/worker",
        "--requeue",
    )

    assert [c[0] for c in capture.calls] == [
        "ingestion_enqueue_sinan",
        "ingestion_enqueue_sinan",
    ]

    first_args = capture.calls[0][1]
    second_args = capture.calls[1][1]

    assert first_args[0] == "/x/es.csv"
    assert "--uf" in first_args
    assert first_args[first_args.index("--uf") + 1] == "ES"
    assert second_args[0] == "/x/br.csv"


@pytest.mark.django_db
def test_manifest_dry_run_does_not_call_enqueue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    --dry-run does not call ingestion_enqueue_sinan.
    """
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps([{"dest": "/x/a.csv"}]), encoding="utf-8"
    )

    capture = _CallCapture()
    monkeypatch.setattr(man, "call_command", capture)

    call_command(
        "ingestion_enqueue_manifest",
        "--manifest",
        str(manifest_path),
        "--dry-run",
    )

    assert capture.calls == []
