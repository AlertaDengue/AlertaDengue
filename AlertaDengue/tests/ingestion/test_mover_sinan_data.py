from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from ingestion.management.commands import mover_sinan_data as mover


def _write_csv(path: Path, content: str) -> None:
    """
    Write a CSV file as UTF-8 text.

    Parameters
    ----------
    path
        Destination path.
    content
        CSV content.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_move_to_canonical_csv_dry_run_bucket_es(tmp_path: Path) -> None:
    """
    A CSV with SG_UF_NOT=ES buckets to 'es' and includes ES in filename.
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


def test_csv_priority_prefers_sg_uf_not_over_sg_uf(tmp_path: Path) -> None:
    """
    CSV priority: SG_UF_NOT > SG_UF > UF.

    If SG_UF_NOT is single-UF (ES) but SG_UF is mixed, bucket must be 'es'.
    """
    src = tmp_path / "incoming" / "mix.csv"
    _write_csv(
        src,
        "ID_AGRAVO;SEM_NOT;SG_UF_NOT;SG_UF\n"
        "A90;202605;ES;SP\n"
        "A90;202605;ES;MG\n",
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
    assert "/imported/es/" in dest.as_posix()
    assert dest.name == "DenInfodengue_ES_202605.csv"


def test_collision_versioning_creates_suffix_with_bucket(
    tmp_path: Path,
) -> None:
    """
    If canonical exists with different content, version to _01 and keep bucket
    label in the filename.
    """
    imported_base = tmp_path / "imported"
    uploaded_base = tmp_path / "uploaded"

    existing = (
        uploaded_base / "br/csv/dengue/2026/202605/DenInfodengue_BR_202605.csv"
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
    assert dest.name == "DenInfodengue_BR_202605_01.csv"


def test_checksum_skip_if_identical_exists(tmp_path: Path) -> None:
    """
    If destination exists with the same checksum, return SKIP.

    This checks the uploaded/imported checksum dedupe.
    """
    imported_base = tmp_path / "imported"
    uploaded_base = tmp_path / "uploaded"

    content = "ID_AGRAVO;SEM_NOT\nA90;202605\n"
    existing = (
        uploaded_base / "br/csv/dengue/2026/202605/DenInfodengue_BR_202605.csv"
    )
    _write_csv(existing, content)

    src = tmp_path / "incoming" / "same.csv"
    _write_csv(src, content)

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

    assert ok is False
    assert dest is None
    assert info is not None
    assert err is not None
    assert err.startswith("SKIP")


@dataclass(frozen=True, slots=True)
class _FakeDBF:
    """
    Fake DBF reader for deterministic bucketing-priority tests.
    """

    field_names: list[str]
    records: list[dict[str, Any]]

    def __iter__(self) -> Any:
        return iter(self.records)


def test_dbf_priority_prefers_sg_uf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    DBF priority: SG_UF > SG_UF_NOT > UF.

    SG_UF is single-UF (SP) while SG_UF_NOT is mixed -> bucket must be 'sp'.
    """
    incoming = tmp_path / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    src = incoming / "file.dbf"
    src.write_bytes(b"not-a-real-dbf")

    fields = ["ID_AGRAVO", "SEM_NOT", "SG_UF", "SG_UF_NOT", "UF"]
    records = [
        {
            "ID_AGRAVO": b"A92.0",
            "SEM_NOT": b"202452",
            "SG_UF": b"35",
            "SG_UF_NOT": b"35",
            "UF": b"35",
        },
        {
            "ID_AGRAVO": b"A92.0",
            "SEM_NOT": b"202452",
            "SG_UF": b"35",
            "SG_UF_NOT": b"32",
            "UF": b"35",
        },
    ]

    def _fake_dbf(*_: Any, **__: Any) -> _FakeDBF:
        return _FakeDBF(field_names=fields, records=records)

    monkeypatch.setattr(mover, "DBF", _fake_dbf)

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
        fmt_dir="dbf",
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
        "/imported/sp/dbf/chik/2024/202452/ChikInfodengue_SP_202452.dbf"
    )


def test_main_writes_sorted_manifest_es_before_br(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Manifest should list ES before BR when both are present.
    """
    imported_base = tmp_path / "imported"
    uploaded_base = tmp_path / "uploaded"

    es_src = tmp_path / "incoming" / "a.csv"
    br_src = tmp_path / "incoming" / "b.csv"

    _write_csv(es_src, "CID10;SEM_NOT;SG_UF_NOT\nA90;202606;ES\n")
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


def test_move_to_canonical_outdated_skip(tmp_path: Path) -> None:
    """
    If file is older than epiweek-window, it should be skipped.
    """
    src = tmp_path / "incoming" / "old.csv"
    # 202301 is definitively old
    _write_csv(src, "ID_AGRAVO;SEM_NOT;SG_UF_NOT\nA90;202301;ES\n")

    ok, dest, info, err = mover.move_to_canonical(
        src,
        imported_base=tmp_path / "imported",
        uploaded_base=tmp_path / "uploaded",
        reserved_relpaths=set(),
        dry_run=True,
        include_uf=False,
        country=None,
        fmt_dir=None,
        csv_encoding=None,
        try_csv_encodings=["utf-8"],
        dbf_encoding="iso-8859-1",
        on_exists="version",
        epiweek_window=58,
    )

    assert ok is False
    assert err is not None
    assert "OUTDATED" in err


def test_move_to_canonical_outdated_allow(tmp_path: Path) -> None:
    """
    If allow_outdated=True, even an old file is moved.
    """
    src = tmp_path / "incoming" / "old.csv"
    _write_csv(src, "ID_AGRAVO;SEM_NOT;SG_UF_NOT\nA90;202301;ES\n")

    ok, dest, info, err = mover.move_to_canonical(
        src,
        imported_base=tmp_path / "imported",
        uploaded_base=tmp_path / "uploaded",
        reserved_relpaths=set(),
        dry_run=True,
        include_uf=False,
        country=None,
        fmt_dir=None,
        csv_encoding=None,
        try_csv_encodings=["utf-8"],
        dbf_encoding="iso-8859-1",
        on_exists="version",
        epiweek_window=58,
        allow_outdated=True,
    )

    assert ok is True
    assert err is None


def test_main_with_include_existing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    If --include-existing is set, skipped files (already moved) are in manifest.
    """
    imported_base = tmp_path / "imported"
    uploaded_base = tmp_path / "uploaded"
    src = tmp_path / "incoming" / "existing.csv"
    content = "ID_AGRAVO;SEM_NOT;SG_UF_NOT\nA90;202610;ES\n"
    _write_csv(src, content)

    # Pre-populate uploaded so it will be skipped
    canonical_dest = (
        uploaded_base / "es/csv/dengue/2026/202610/DenInfodengue_ES_202610.csv"
    )
    _write_csv(canonical_dest, content)

    manifest_path = tmp_path / "manifest.json"
    argv = [
        "mover_sinan_data.py",
        str(src),
        "--imported-base",
        str(imported_base),
        "--uploaded-base",
        str(uploaded_base),
        "--manifest",
        str(manifest_path),
        "--include-existing",
        "--dry-run",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    exit_code = mover.main()

    assert exit_code == 0
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(entries) == 1
    assert entries[0]["dest"] == str(canonical_dest)
