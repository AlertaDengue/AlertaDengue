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


def test_pg18_marker_is_exact_nested_layout(tmp_path: Path) -> None:
    source = tmp_path / "pg14"
    target = tmp_path / "pg18"
    source.mkdir()
    target.mkdir()
    (source / "PG_VERSION").write_text("14\n", encoding="utf-8")
    (target / "18" / "docker").mkdir(parents=True)
    (target / "18" / "docker" / "PG_VERSION").write_text(
        "18\n", encoding="utf-8"
    )
    validate_deployment_paths(str(source), str(target), mode="cutover")


def test_steady_state_does_not_require_pg14(tmp_path: Path) -> None:
    target = tmp_path / "pg18"
    (target / "18" / "docker").mkdir(parents=True)
    (target / "18" / "docker" / "PG_VERSION").write_text(
        "18\n", encoding="utf-8"
    )
    validate_deployment_paths("", str(target), mode="steady-state")


def test_empty_pg18_parent_is_not_steady_state(tmp_path: Path) -> None:
    target = tmp_path / "pg18"
    target.mkdir()
    with pytest.raises(PreflightError, match="steady-state"):
        validate_deployment_paths("", str(target), mode="steady-state")


def test_initialization_requires_completely_empty_target_without_pg14(
    tmp_path: Path,
) -> None:
    target = tmp_path / "pg18"
    target.mkdir()
    validate_deployment_paths("", str(target), mode="initialization")
    (target / "18").mkdir()
    with pytest.raises(PreflightError, match="empty"):
        validate_deployment_paths("", str(target), mode="initialization")


def test_empty_source_is_not_resolved_to_cwd(tmp_path: Path) -> None:
    target = tmp_path / "pg18"
    target.mkdir()
    source, _ = validate_deployment_paths(
        "", str(target), mode="initialization"
    )
    assert source is None


def test_steady_state_rejects_stale_cluster_state(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "pg18"
    (target / "18" / "docker").mkdir(parents=True)
    (target / "18" / "docker" / "PG_VERSION").write_text(
        "18\n", encoding="ascii"
    )
    state = tmp_path / "state"
    state.write_text(
        __import__("json").dumps(
            {
                "state": "validated",
                "target_path": str(target.resolve()),
                "postgres_major": "18",
                "system_identifier": "old",
            }
        ),
        encoding="utf-8",
    )

    class Result:
        stdout = "Database system identifier: new\n"

    monkeypatch.setattr(
        "containers.postgres.deployment_preflight.subprocess.run",
        lambda *args, **kwargs: Result(),
    )
    with pytest.raises(PreflightError, match="another cluster"):
        validate_deployment_paths(
            "",
            str(target),
            mode="steady-state",
            state_file=state,
            require_validated_state=True,
                postgres_image="local-postgres:18",
            )


def test_steady_state_rejects_state_for_another_target(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "pg18"
    (target / "18" / "docker").mkdir(parents=True)
    (target / "18" / "docker" / "PG_VERSION").write_text(
        "18\n", encoding="ascii"
    )
    state = tmp_path / "state"
    state.write_text(
        __import__("json").dumps(
            {
                "state": "validated",
                "target_path": str((tmp_path / "other").resolve()),
                "postgres_major": "18",
                "system_identifier": "same",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(PreflightError, match="does not match target"):
        validate_deployment_paths(
            "",
            str(target),
            mode="steady-state",
            state_file=state,
            require_validated_state=True,
        )


def test_preflight_failure_preserves_existing_state(tmp_path: Path) -> None:
    source = tmp_path / "pg14"
    target = tmp_path / "pg18"
    source.mkdir()
    target.mkdir()
    (source / "PG_VERSION").write_text("13\n", encoding="ascii")
    state = tmp_path / "pg18.migration-state"
    original = b'{"state":"validated"}\n'
    state.write_bytes(original)

    with pytest.raises(PreflightError, match="PostgreSQL 14"):
        validate_deployment_paths(str(source), str(target), mode="cutover")

    assert state.read_bytes() == original


def test_restore_validation_accepts_pg18_without_state(tmp_path: Path) -> None:
    target = tmp_path / "pg18"
    (target / "18" / "docker").mkdir(parents=True)
    (target / "18" / "docker" / "PG_VERSION").write_text(
        "18\n", encoding="ascii"
    )

    validate_deployment_paths("", str(target), mode="restore-validation")
    with pytest.raises(PreflightError, match="validated migration state"):
        validate_deployment_paths(
            "",
            str(target),
            mode="steady-state",
            state_file=tmp_path / "pg18.migration-state",
            require_validated_state=True,
        )


def test_system_identifier_uses_read_only_repository_image(
    monkeypatch, tmp_path: Path
) -> None:
    from containers.postgres import deployment_preflight

    target = tmp_path / "pg18"
    target.mkdir()
    calls = []

    class Result:
        stdout = "Database system identifier: 123\n"

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr(deployment_preflight.subprocess, "run", fake_run)
    assert deployment_preflight._cluster_system_identifier(target, "configured-postgres:18") == "123"
    command = calls[0]
    assert command[0:3] == ["docker", "run", "--rm"]
    assert "pg_controldata" not in command[0]
    assert "--read-only" in command
    assert "configured-postgres:18" in command
    assert any("readonly" in item for item in command)


def test_system_identifier_requires_configured_image(tmp_path: Path) -> None:
    from containers.postgres import deployment_preflight

    with pytest.raises(PreflightError, match="PostgreSQL image is required"):
        deployment_preflight._cluster_system_identifier(tmp_path, "")


def test_restore_validation_commands_use_guarded_nonempty_connection_values() -> None:
    makim = Path(".makim.yaml").read_text(encoding="utf-8")
    assert '--target-port ""' not in makim
    assert '--target-database ""' not in makim
    assert '--target-user ""' not in makim
    assert 'PGPASSWORD=""' not in makim
    assert 'PGPASSFILE="$(mktemp)"' in makim
    assert ': "${PSQL_DB:?PSQL_DB is required}"' in makim
    assert ': "${PSQL_USER:?PSQL_USER is required}"' in makim
    assert ': "${PG18_HOST_PGDATA:?PG18_HOST_PGDATA is required}"' in makim
    assert '--target-port "$TARGET_PG_PORT"' in makim
    assert '--postgres-image "${PG18_POSTGRES_IMAGE:?' in makim
