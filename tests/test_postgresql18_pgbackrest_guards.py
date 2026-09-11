from pathlib import Path

from containers.pgbackrest.refresh_staging import (
    ValidationError,
    select_backup_from_info,
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


def test_pg14_physical_backup_is_rejected_before_cleanup(tmp_path: Path) -> None:
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
    assert select_backup_from_info(
        _info("180006"),
        stanza_name="prod",
        backup_label="20260909-120000F",
        target_major=18,
    ) == 1024


def test_pg14_to_pg18_logical_migration_remains_accepted() -> None:
    validate_versions("14.13", "18.6")
