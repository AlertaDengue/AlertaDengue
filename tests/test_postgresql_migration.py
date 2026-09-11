import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

SPEC = importlib.util.spec_from_file_location(
    "postgres_migration", "containers/postgres/migration.py"
)
migration = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["postgres_migration"] = migration
SPEC.loader.exec_module(migration)


def endpoint(host: str = "source") -> migration.Endpoint:
    return migration.Endpoint(host, "5432", "db", "operator", "secret")


def paths(tmp_path: Path) -> tuple[Path, Path]:
    source, target = tmp_path / "pg14", tmp_path / "pg18"
    source.mkdir()
    target.mkdir()
    (source / "PG_VERSION").write_text("14\n", encoding="ascii")
    return source, target


def test_paths_require_absolute_separate_pg14_source_and_empty_target(
    tmp_path: Path,
) -> None:
    source, target = paths(tmp_path)
    migration.validate_storage_paths(source, target)
    with pytest.raises(migration.MigrationError, match="absolute"):
        migration.validate_storage_paths(Path("relative"), target)
    (target / "file").write_text("x", encoding="ascii")
    with pytest.raises(migration.MigrationError, match="not empty"):
        migration.validate_storage_paths(source, target)


def test_source_marker_and_nested_target_are_rejected(tmp_path: Path) -> None:
    source, target = paths(tmp_path)
    (source / "PG_VERSION").write_text("13\n", encoding="ascii")
    with pytest.raises(migration.MigrationError, match="PG_VERSION=14"):
        migration.validate_storage_paths(source, target)
    (source / "PG_VERSION").write_text("14\n", encoding="ascii")
    (source / "nested").mkdir()
    with pytest.raises(migration.MigrationError, match="separate siblings"):
        migration.validate_storage_paths(source, source / "nested")


def test_preflight_checks_disk_and_client_commands(tmp_path: Path, monkeypatch) -> None:
    with pytest.raises(migration.MigrationError, match="does not exist"):
        migration.validate_free_space(tmp_path / "missing", 1)

    monkeypatch.setattr(migration.shutil, "which", lambda _: None)
    with pytest.raises(migration.MigrationError, match="unavailable"):
        migration.validate_client_commands()
def test_commands_accept_only_the_arguments_they_need(tmp_path: Path) -> None:
    parser = migration.build_parser()
    dump = parser.parse_args(
        [
            "dump", "--source-host", "source", "--source-port", "5432",
            "--source-database", "db", "--source-user", "user",
            "--output-dir", str(tmp_path / "dump"),
        ]
    )
    assert dump.action == "dump"
    preflight = parser.parse_args(
        [
            "preflight", "--source-host", "source", "--source-port", "5432",
            "--source-database", "db", "--source-user", "user",
            "--source-path", str(tmp_path / "source"), "--target-path",
            str(tmp_path / "target"), "--disk-path", str(tmp_path),
            "--required-bytes", "1",
        ]
    )
    assert preflight.action == "preflight"


def test_commands_never_include_password_and_errors_redact_it(monkeypatch) -> None:
    calls = []

    def fail(args, **kwargs):
        calls.append((args, kwargs))
        raise migration.subprocess.CalledProcessError(1, args)

    monkeypatch.setattr(migration.subprocess, "run", fail)
    with pytest.raises(migration.MigrationError) as error:
        migration.run_command(["psql", "-U", "operator"], "secret")
    assert "secret" not in calls[0][0]
    assert calls[0][1]["env"]["PGPASSWORD"] == "secret"
    assert "secret" not in str(error.value)


def test_dump_is_private_and_archive_is_checked(monkeypatch, tmp_path: Path) -> None:
    archive = tmp_path / "database.dump"
    calls = []

    def command(args, *_):
        calls.append(args)
        if args[0] == "pg_dump":
            archive.write_bytes(b"archive")
        return ""

    monkeypatch.setattr(migration, "run_command", command)
    migration.dump_database(endpoint(), archive)
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600
    assert calls[0][0] == "pg_dump"
    assert calls[1][:2] == ["pg_restore", "--list"]


def test_existing_dump_directory_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "dump"
    output.mkdir()
    with pytest.raises(migration.MigrationError, match="already exists"):
        migration.prepare_output_directory(output)


def test_restore_requires_pg18_empty_target_and_fail_fast(monkeypatch, tmp_path: Path) -> None:
    archive = tmp_path / "database.dump"
    archive.write_bytes(b"archive")
    commands = []

    def scalar(_, query):
        return "180006" if "server_version_num" in query else "0"

    monkeypatch.setattr(migration, "scalar", scalar)
    monkeypatch.setattr(migration, "validate_archive", lambda _: None)
    monkeypatch.setattr(
        migration,
        "run_command",
        lambda args, *_: commands.append(args) or "",
    )
    migration.restore(endpoint("target"), archive)
    restore = commands[-1]
    for option in (
        "--no-owner",
        "--no-acl",
        "--single-transaction",
        "--exit-on-error",
        "--role=operator",
    ):
        assert option in restore
    monkeypatch.setattr(
        migration,
        "run_command",
        lambda *_: (_ for _ in ()).throw(migration.MigrationError("stop")),
    )
    with pytest.raises(migration.MigrationError, match="stop"):
        migration.restore(endpoint("target"), archive)


def test_validation_checks_distinct_endpoints_and_contract(monkeypatch) -> None:
    source, target = endpoint(), endpoint("target")
    answers = iter(
        [
            "140013", "180006", "postgis,hstore,plpython3u,postgres_fdw",
            ",".join(sorted(migration.APPLICATION_SCHEMAS)), "t", "1",
            "t", "t", "t", "t", "t", "0", "0", "0", "",
        ]
    )
    monkeypatch.setattr(migration, "scalar", lambda *_: next(answers))
    migration.validate_contract(source, target)
    with pytest.raises(migration.MigrationError, match="different"):
        migration.validate_contract(source, source)


def test_entrypoint_requires_explicit_one_time_initialization_guard() -> None:
    script = Path("containers/postgres/scripts/entrypoint.sh").read_text()
    assert "ALLOW_PG18_INITIALIZATION" in script
    assert "conflicting PG_VERSION" in script
    assert "Refusing to initialize empty PG18 data directory" in script

@pytest.mark.parametrize("profile", ["dev", "staging", "prod"])
def test_rendered_profile_stanza_environment_is_deterministic(profile: str) -> None:
    environment = {
        **os.environ,
        "ENV": "dev",
        "PG18_POSTGRES_IMAGE": "alertadengue-postgres:18.6-bookworm",
        "PG18_HOST_PGDATA": "/tmp/pg18-compose-test",
        "PSQL_PASSWORD": "render-only",
        "PSQL_DB": "db",
        "PSQL_USER": "user",
        "PSQL_PORT": "55432",
        "PSQL_HOST_PORT": "55433",
        "PG_ARCHIVE_MODE": "on",
    }
    result = subprocess.run(
        [
            "docker", "compose", "--env-file", ".envs/.env",
            "-f", "containers/compose-base.yaml",
            "-f", f"containers/compose-{profile}.yaml",
            "config", "--format", "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    postgres = json.loads(result.stdout)["services"]["postgres"]
    expected = {"dev": "dev", "staging": "staging", "prod": "prod"}[profile]
    assert postgres["environment"]["ENV"] == expected
    assert postgres["environment"]["PG_STANZA"] == expected
    assert postgres["environment"]["PGDATA"] == "/var/lib/postgresql/18/docker"


def test_rendered_staging_can_disable_archive_mode() -> None:
    environment = {
        **os.environ,
        "ENV": "dev",
        "PG18_POSTGRES_IMAGE": "alertadengue-postgres:18.6-bookworm",
        "PG18_HOST_PGDATA": "/tmp/pg18-compose-test",
        "PSQL_PASSWORD": "render-only",
        "PSQL_DB": "db",
        "PSQL_USER": "user",
        "PSQL_PORT": "55432",
        "PSQL_HOST_PORT": "55433",
        "PG_ARCHIVE_MODE": "off",
    }
    result = subprocess.run(
        [
            "docker", "compose", "--env-file", ".envs/.env",
            "-f", "containers/compose-base.yaml",
            "-f", "containers/compose-staging.yaml",
            "config", "--format", "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    postgres = json.loads(result.stdout)["services"]["postgres"]
    assert postgres["environment"]["PG_ARCHIVE_MODE"] == "off"

ADMINPACK_TOC = (
    "1; 0 0 TABLE - users\n"
    "2; 3079 1262 EXTENSION - adminpack\n"
    "3; 0 0 COMMENT - EXTENSION \"adminpack\"\n"
    "4; 0 0 TABLE - orders\n"
)


def test_filter_restore_list_removes_only_adminpack_pair() -> None:
    filtered = migration.filter_restore_list(ADMINPACK_TOC)
    assert "EXTENSION - adminpack" not in filtered
    assert 'COMMENT - EXTENSION "adminpack"' not in filtered
    assert "TABLE - users" in filtered
    assert "TABLE - orders" in filtered


def test_filter_restore_list_accepts_archive_without_adminpack() -> None:
    toc = "1; 0 0 TABLE - users\n2; 0 0 TABLE - orders\n"
    assert migration.filter_restore_list(toc) == toc


@pytest.mark.parametrize(
    "toc",
    [
        "1; 3079 1262 EXTENSION - adminpack\n",
        "1; 0 0 COMMENT - EXTENSION \"adminpack\"\n",
    ],
)
def test_filter_restore_list_rejects_partial_adminpack_pair(toc: str) -> None:
    with pytest.raises(migration.MigrationError, match="partial"):
        migration.filter_restore_list(toc)


def test_filter_restore_list_rejects_unexpected_adminpack_entry() -> None:
    toc = "1; 0 0 FUNCTION - adminpack_helper\n"
    with pytest.raises(migration.MigrationError, match="unexpected"):
        migration.filter_restore_list(toc)


def test_restore_uses_private_filtered_list_and_removes_it(
    monkeypatch, tmp_path: Path
) -> None:
    archive = tmp_path / "database.dump"
    archive.write_bytes(b"archive")
    calls = []
    responses = iter([ADMINPACK_TOC, ""])

    def command(args, *_):
        calls.append(args)
        return next(responses)

    monkeypatch.setattr(migration, "scalar", lambda *_: "180006" if "version" in _[-1] else "0")
    monkeypatch.setattr(migration, "run_command", command)
    migration.restore(endpoint("target"), archive)
    assert any(arg.startswith("--use-list=") for arg in calls[1])
    assert "--single-transaction" in calls[1]
    assert "--exit-on-error" in calls[1]
    assert not list(tmp_path.glob(".postgres-restore-*.list"))


def test_restore_list_is_removed_after_pg_restore_failure(
    monkeypatch, tmp_path: Path
) -> None:
    archive = tmp_path / "database.dump"
    archive.write_bytes(b"archive")
    calls = []

    def command(args, *_):
        calls.append(args)
        if len(calls) == 1:
            return ADMINPACK_TOC
        raise migration.MigrationError("restore failed")

    monkeypatch.setattr(migration, "scalar", lambda *_: "180006" if "version" in _[-1] else "0")
    monkeypatch.setattr(migration, "run_command", command)
    with pytest.raises(migration.MigrationError, match="restore failed"):
        migration.restore(endpoint("target"), archive)
    assert not list(tmp_path.glob(".postgres-restore-*.list"))


def test_restore_list_has_private_permissions(monkeypatch, tmp_path: Path) -> None:
    archive = tmp_path / "database.dump"
    archive.write_bytes(b"archive")
    restore_list = migration.write_restore_list(archive, ADMINPACK_TOC)
    try:
        assert stat.S_IMODE(restore_list.stat().st_mode) == 0o600
    finally:
        restore_list.unlink()
