from pathlib import Path

from containers.pgbackrest.refresh_staging import (
    ValidationError,
    select_backup_from_info,
)
from containers.postgres.deployment_preflight import (
    PreflightError,
    validate_deployment_paths,
)
from containers.postgres.migration import validate_versions
import pytest


def _info(version: str) -> list[dict]:
    return [
        {
            "name": "prod",
            "repo": [{"status": {"code": 0, "message": "ok"}}],
            "db": [{"version": version}],
            "backup": [
                {
                    "label": "20260909-120000F",
                    "type": "full",
                    "info": {"size": 1024},
                }
            ],
        }
    ]


def test_pg14_physical_backup_is_rejected_for_pg18_before_cleanup(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    sentinel = target / "must-remain"
    sentinel.write_text("untouched", encoding="utf-8")

    with pytest.raises(ValidationError, match="match target PostgreSQL 18"):
        select_backup_from_info(
            _info("14"),
            stanza_name="prod",
            backup_label="20260909-120000F",
            target_major=18,
        )

    assert sentinel.read_text(encoding="utf-8") == "untouched"


def test_pg18_physical_backup_is_accepted_for_pg18() -> None:
    assert (
        select_backup_from_info(
            _info("180006"),
            stanza_name="prod",
            backup_label="20260909-120000F",
            target_major=18,
        )
        == 1024
    )


def test_pg14_to_pg18_logical_migration_remains_accepted() -> None:
    validate_versions("14.13", "18.6")


def test_deployment_preflight_rejects_missing_pg18_target(
    tmp_path: Path,
) -> None:
    source = tmp_path / "pg14"
    source.mkdir()
    (source / "PG_VERSION").write_text("14\n", encoding="utf-8")

    with pytest.raises(PreflightError, match="target is unavailable"):
        validate_deployment_paths(str(source), str(tmp_path / "missing-18"))


@pytest.mark.parametrize(
    "target_kind",
    ["same", "nested"],
)
def test_deployment_preflight_rejects_ambiguous_target(
    tmp_path: Path, target_kind: str
) -> None:
    source = tmp_path / "pg14"
    source.mkdir()
    (source / "PG_VERSION").write_text("14\n", encoding="utf-8")
    target = source if target_kind == "same" else source / "pg18"
    if target_kind == "nested":
        target.mkdir()

    with pytest.raises(PreflightError, match="must"):
        validate_deployment_paths(str(source), str(target))


def test_deployment_preflight_rejects_non_pg18_target(tmp_path: Path) -> None:
    source = tmp_path / "pg14"
    target = tmp_path / "pg18"
    source.mkdir()
    target.mkdir()
    (source / "PG_VERSION").write_text("14\n", encoding="utf-8")
    (target / "PG_VERSION").write_text("14\n", encoding="utf-8")

    with pytest.raises(PreflightError, match="non-PostgreSQL-18"):
        validate_deployment_paths(str(source), str(target))
