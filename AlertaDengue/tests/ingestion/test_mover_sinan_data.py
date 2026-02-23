from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from ingestion.management.commands import mover_sinan_data as mover


def _write_csv(path: Path, content: str) -> None:
    """
    Write a CSV file as text.

    Parameters
    ----------
    path
        Destination path.
    content
        CSV content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_move_to_canonical_csv_dry_run(tmp_path: Path) -> None:
    """
    It computes the canonical destination for a CSV in dry-run mode.
    """
    src = tmp_path / "incoming" / "DENGON_ES_202605_Infodengue.csv"
    _write_csv(
        src,
        "ID_AGRAVO;SEM_NOT;SG_UF_NOT\n" "A90;202605;ES\n" "A90;202605;ES\n",
    )

    imported_base = tmp_path / "imported"
    uploaded_base = tmp_path / "uploaded"
    ok, dest, info, err = mover.move_to_canonical(
        src,
        imported_base=imported_base,
        uploaded_base=uploaded_base,
        reserved_relpaths=set(),
        dry_run=True,
        include_uf=False,
        country=None,
        fmt_dir=None,
        csv_encoding=None,
        try_csv_encodings=["utf-8"],
        dbf_encoding="iso-8859-1",
        on_exists="version",
    )

    assert ok is True
    assert err is None
    assert info is not None
    assert dest is not None
    assert dest.as_posix().endswith(
        "/imported/es/csv/dengue/2026/202605/DenInfodengue_ES_202605.csv"
    )


def test_collision_versioning_creates_suffix(tmp_path: Path) -> None:
    """
    When canonical exists with a different checksum, it versions the filename.
    """
    imported_base = tmp_path / "imported"
    uploaded_base = tmp_path / "uploaded"

    existing = (
        uploaded_base / "br/csv/dengue/2026/202605/DenInfodengue_202605.csv"
    )
    _write_csv(existing, "ID_AGRAVO;SEM_NOT\nA90;202605\n")

    src = tmp_path / "incoming" / "new.csv"
    _write_csv(src, "ID_AGRAVO;SEM_NOT\nA90;202605\nA90;202605\n")

    ok, dest, info, err = mover.move_to_canonical(
        src,
        imported_base=imported_base,
        uploaded_base=uploaded_base,
        reserved_relpaths=set(),
        dry_run=True,
        include_uf=False,
        country="br",
        fmt_dir="csv",
        csv_encoding="utf-8",
        try_csv_encodings=["utf-8"],
        dbf_encoding="iso-8859-1",
        on_exists="version",
    )

    assert ok is True
    assert err is None
    assert info is not None
    assert dest is not None
    assert dest.name == "DenInfodengue_202605_01.csv"


def test_main_writes_sorted_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Manifest is sorted with ES entries first, then by sem_not_max.
    """
    imported_base = tmp_path / "imported"
    uploaded_base = tmp_path / "uploaded"

    es_src = tmp_path / "incoming" / "es" / "a.csv"
    br_src = tmp_path / "incoming" / "br" / "b.csv"

    _write_csv(es_src, "CID10;SEM_NOT\nA90;202606\n")
    _write_csv(br_src, "CID10;SEM_NOT\nA90;202605\n")

    manifest_path = tmp_path / "manifest.json"

    argv = [
        "mover_sinan_data.py",
        str(es_src),
        str(br_src),
        "--imported-base",
        str(imported_base),
        "--uploaded-base",
        str(uploaded_base),
        "--manifest",
        str(manifest_path),
        "--dry-run",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    exit_code = mover.main()

    assert exit_code == 0
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert entries[0]["country"] == "es"
    assert entries[1]["country"] == "br"
