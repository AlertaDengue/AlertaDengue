from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from containers.pgbackrest.refresh_staging import (
    APPROVED_PGDATA_ROOTS_BY_PROFILE,
    ValidationError,
    select_backup_from_info,
    validate_full_backup_label,
    validate_profile_restore_inputs,
    validate_refresh_inputs,
    validate_restored_database,
    validate_volume_labels,
)


@pytest.fixture
def approved_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "approved-staging-root"
    root.mkdir()
    monkeypatch.setattr(
        "containers.pgbackrest.refresh_staging.APPROVED_PGDATA_ROOTS_BY_PROFILE",
        {
            **APPROVED_PGDATA_ROOTS_BY_PROFILE,
            "staging": (root,),
        },
    )
    return root


@pytest.fixture
def approved_dev_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "approved-dev-root"
    root.mkdir()
    monkeypatch.setattr(
        "containers.pgbackrest.refresh_staging.APPROVED_PGDATA_ROOTS_BY_PROFILE",
        {
            **APPROVED_PGDATA_ROOTS_BY_PROFILE,
            "dev": (root,),
        },
    )
    return root


def _build_source_repo(root: Path) -> Path:
    repo = root / "pgbackrest-prod-repo"
    (repo / "backup" / "prod").mkdir(parents=True)
    (repo / "archive" / "prod").mkdir(parents=True)
    (repo / "backup" / "prod" / "backup.info").write_text("backup", encoding="utf-8")
    (repo / "archive" / "prod" / "archive.info").write_text("archive", encoding="utf-8")
    return repo


def test_invalid_confirmation_rejected(tmp_path: Path, approved_root: Path) -> None:
    source_repo = _build_source_repo(tmp_path)
    host_pgdata = approved_root / "db"
    host_pgdata.mkdir(parents=True)

    with pytest.raises(ValidationError, match="REFRESH-STAGING-FROM-PROD"):
        validate_refresh_inputs(
            source_repo=str(source_repo),
            host_pgdata=str(host_pgdata),
            backup_set="20260711-123456F",
            confirm="WRONG",
        )


def test_invalid_full_backup_label_rejected() -> None:
    with pytest.raises(ValidationError, match="full backup label"):
        validate_full_backup_label("20260711-123456D")


def test_invalid_profile_restore_confirmation_rejected(approved_dev_root: Path) -> None:
    host_pgdata = approved_dev_root / "pgdata"
    host_pgdata.mkdir()

    with pytest.raises(ValidationError, match="RESTORE-PROFILE-BACKUP"):
        validate_profile_restore_inputs(
            profile="dev",
            host_pgdata=str(host_pgdata),
            backup_set="20260711-123456F",
            confirm="RESTORE-LATEST",
        )


def test_relative_source_repo_rejected(tmp_path: Path, approved_root: Path) -> None:
    host_pgdata = approved_root / "db"
    host_pgdata.mkdir(parents=True)

    with pytest.raises(ValidationError, match="absolute path"):
        validate_refresh_inputs(
            source_repo="relative/repo",
            host_pgdata=str(host_pgdata),
            backup_set="20260711-123456F",
            confirm="REFRESH-STAGING-FROM-PROD",
        )


def test_relative_pgdata_rejected(tmp_path: Path) -> None:
    source_repo = _build_source_repo(tmp_path)

    with pytest.raises(ValidationError, match="HOST_PGDATA must be an absolute path"):
        validate_refresh_inputs(
            source_repo=str(source_repo),
            host_pgdata="relative/pgdata",
            backup_set="20260711-123456F",
            confirm="REFRESH-STAGING-FROM-PROD",
        )


def test_profile_restore_rejects_path_outside_approved_profile_root(
    tmp_path: Path, approved_dev_root: Path
) -> None:
    host_pgdata = tmp_path / "outside-root" / "pgdata"
    host_pgdata.mkdir(parents=True)

    with pytest.raises(ValidationError, match="approved profile root"):
        validate_profile_restore_inputs(
            profile="dev",
            host_pgdata=str(host_pgdata),
            backup_set="20260711-123456F",
            confirm="RESTORE-PROFILE-BACKUP",
        )


def test_profile_restore_accepts_valid_explicit_backup(
    approved_dev_root: Path,
) -> None:
    host_pgdata = approved_dev_root / "pgdata"
    host_pgdata.mkdir()

    result = validate_profile_restore_inputs(
        profile="dev",
        host_pgdata=str(host_pgdata),
        backup_set="20260711-123456F",
        confirm="RESTORE-PROFILE-BACKUP",
    )

    assert result.profile == "dev"
    assert result.host_pgdata == host_pgdata.resolve()
    assert result.backup_set == "20260711-123456F"


@pytest.mark.parametrize(
    "forbidden_root",
    ["/", "/var", "/opt", "/srv", "/Storage", "/home"],
)
def test_forbidden_pgdata_roots_rejected(
    tmp_path: Path,
    forbidden_root: str,
    approved_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_repo = _build_source_repo(tmp_path)
    fake_realpath = lambda path: forbidden_root if path == forbidden_root else str(source_repo)
    monkeypatch.setattr("containers.pgbackrest.refresh_staging.os.path.realpath", fake_realpath)

    with pytest.raises(ValidationError, match="forbidden path"):
        validate_refresh_inputs(
            source_repo=str(source_repo),
            host_pgdata=forbidden_root,
            backup_set="20260711-123456F",
            confirm="REFRESH-STAGING-FROM-PROD",
        )


def test_symbolic_link_pgdata_rejected(tmp_path: Path, approved_root: Path) -> None:
    source_repo = _build_source_repo(tmp_path)
    real_pgdata = approved_root / "real-db"
    real_pgdata.mkdir(parents=True)
    link_pgdata = approved_root / "db-link"
    link_pgdata.symlink_to(real_pgdata)

    with pytest.raises(ValidationError, match="symbolic link"):
        validate_refresh_inputs(
            source_repo=str(source_repo),
            host_pgdata=str(link_pgdata),
            backup_set="20260711-123456F",
            confirm="REFRESH-STAGING-FROM-PROD",
        )


@pytest.mark.parametrize(
    "pgdata_suffix",
    ["", "nested", "../pgbackrest-prod-repo"],
)
def test_overlapping_source_repo_and_pgdata_rejected(
    tmp_path: Path, approved_root: Path, pgdata_suffix: str
) -> None:
    source_repo = _build_source_repo(approved_root / "source-root")
    if pgdata_suffix == "":
        host_pgdata = source_repo
    elif pgdata_suffix == "nested":
        host_pgdata = source_repo / "nested"
        host_pgdata.mkdir()
    else:
        host_pgdata = approved_root / "container"
        host_pgdata.mkdir()
        source_repo = _build_source_repo(host_pgdata)

    with pytest.raises(ValidationError, match="source repository"):
        validate_refresh_inputs(
            source_repo=str(source_repo),
            host_pgdata=str(host_pgdata),
            backup_set="20260711-123456F",
            confirm="REFRESH-STAGING-FROM-PROD",
        )


def test_source_repo_without_valid_metadata_rejected(
    tmp_path: Path, approved_root: Path
) -> None:
    repo = tmp_path / "pgbackrest-prod-repo"
    (repo / "backup" / "prod").mkdir(parents=True)
    host_pgdata = approved_root / "db"
    host_pgdata.mkdir(parents=True)

    with pytest.raises(ValidationError, match="Required source path is missing"):
        validate_refresh_inputs(
            source_repo=str(repo),
            host_pgdata=str(host_pgdata),
            backup_set="20260711-123456F",
            confirm="REFRESH-STAGING-FROM-PROD",
        )


def test_incorrect_docker_volume_labels_rejected() -> None:
    with pytest.raises(ValidationError, match="com.docker.compose.project"):
        validate_volume_labels(
            {
                "com.docker.compose.project": "wrong-project",
                "com.docker.compose.volume": "pgbackrest_repo",
            }
        )


def test_quoted_mixed_case_relation_validation() -> None:
    validate_restored_database(
        source_db_size=100,
        data_directory="/var/lib/postgresql/data",
        in_recovery="f",
        relation_exists="t",
        db_size=95,
    )

    with pytest.raises(ValidationError, match="Municipio"):
        validate_restored_database(
            source_db_size=100,
            data_directory="/var/lib/postgresql/data",
            in_recovery="f",
            relation_exists="Dengue_global.Municipio",
            db_size=95,
        )


def test_readiness_timeout_behavior() -> None:
    script = Path("containers/pgbackrest/wait_for_postgres.sh")
    result = subprocess.run(
        ["bash", str(script), "ready"],
        check=False,
        capture_output=True,
        text=True,
        env={
            "POSTGRES_USER": "postgres",
            "POSTGRES_DB": "postgres",
            "TIMEOUT_SECONDS": "2",
            "SLEEP_SECONDS": "0",
            "PG_ISREADY_CMD": "exit 1",
        },
    )

    assert result.returncode == 1
    assert "did not become ready in time" in result.stderr


def test_select_backup_from_info_requires_valid_full_prod_backup() -> None:
    payload = [
        {
            "name": "prod",
            "repo": [{"status": {"code": 0, "message": "ok"}}],
            "db": [{"version": "14"}],
            "backup": [
                {
                    "label": "20260711-123456F",
                    "type": "full",
                    "info": {"size": 1234},
                }
            ],
        }
    ]

    assert (
        select_backup_from_info(
            json.loads(json.dumps(payload)),
            stanza_name="prod",
            backup_label="20260711-123456F",
        )
        == 1234
    )
