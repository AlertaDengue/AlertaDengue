import importlib.util
import sys

import pytest

SPEC = importlib.util.spec_from_file_location(
    "postgres_migration", "containers/postgres/migration.py"
)
migration = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["postgres_migration"] = migration
SPEC.loader.exec_module(migration)


def endpoint(host="source", port="5432", database="db"):
    return migration.Endpoint(host, port, database, "operator", "secret")


@pytest.mark.parametrize(
    ("source", "target", "message"),
    [
        ("13", "18", "source major"),
        ("14", "17", "target major"),
    ],
)
def test_major_version_safeguard(source, target, message):
    with pytest.raises(migration.MigrationError, match=message):
        migration.validate_versions(source, target)


def test_identical_endpoint_is_rejected():
    with pytest.raises(migration.MigrationError, match="different"):
        migration.validate_distinct_endpoints(endpoint(), endpoint())


def test_nonempty_target_is_rejected(monkeypatch):
    monkeypatch.setattr(migration, "scalar", lambda *_: "1")
    with pytest.raises(migration.MigrationError, match="not empty"):
        migration.validate_target_empty(endpoint("target"))


def test_empty_dump_is_rejected(tmp_path):
    dump = tmp_path / "empty.dump"
    dump.touch()
    with pytest.raises(migration.MigrationError, match="empty"):
        migration.validate_archive(dump)


def test_restore_requires_nonempty_globals(tmp_path):
    globals_dump = tmp_path / "globals.sql"
    archive = tmp_path / "database.dump"
    archive.write_bytes(b"archive")
    with pytest.raises(migration.MigrationError, match="globals dump"):
        migration.restore(endpoint("target"), globals_dump, archive)


def test_restore_propagates_command_failure(monkeypatch, tmp_path):
    globals_dump = tmp_path / "globals.sql"
    archive = tmp_path / "database.dump"
    globals_dump.write_text("-- globals")
    archive.write_bytes(b"archive")
    calls = []

    def failing(args, password=None):
        calls.append((args, password))
        if args[0] == "pg_restore":
            raise migration.MigrationError(
                "command failed with exit code 1: pg_restore (credentials omitted)"
            )
        return ""

    monkeypatch.setattr(migration, "run_command", failing)
    with pytest.raises(migration.MigrationError, match="exit code 1"):
        migration.restore(endpoint("target"), globals_dump, archive)
    assert any(call[0][0] == "pg_restore" for call in calls)


def test_password_is_not_in_command_arguments(monkeypatch, tmp_path):
    seen = []

    def fake_run(args, **kwargs):
        seen.append(args)

        class Result:
            stdout = "ok\\n"

        return Result()

    monkeypatch.setattr(migration.subprocess, "run", fake_run)
    migration.run_command(["psql", "-U", "operator"], "super-secret")
    assert "super-secret" not in seen[0]


def test_storage_paths_accept_separate_siblings(tmp_path):
    source = tmp_path / "pg14"
    target = tmp_path / "pg18"
    source.mkdir()
    (source / "PG_VERSION").write_text("14\n")
    target.mkdir()
    migration.validate_storage_paths(
        source, target, container_pgdata="/var/lib/postgresql/18/docker"
    )


def test_storage_paths_reject_nesting(tmp_path):
    source = tmp_path / "pg14"
    source.mkdir()
    (source / "PG_VERSION").write_text("14\n")
    with pytest.raises(migration.MigrationError, match="sibling"):
        migration.validate_storage_paths(
            source,
            source / "pg18",
            container_pgdata="/var/lib/postgresql/18/docker",
        )


def test_storage_paths_reject_wrong_source_marker(tmp_path):
    source = tmp_path / "pg14"
    target = tmp_path / "pg18"
    source.mkdir()
    target.mkdir()
    (source / "PG_VERSION").write_text("13\n")
    with pytest.raises(migration.MigrationError, match="14"):
        migration.validate_storage_paths(
            source, target, container_pgdata="/var/lib/postgresql/18/docker"
        )


def test_storage_paths_reject_nonempty_target(tmp_path):
    source = tmp_path / "pg14"
    target = tmp_path / "pg18"
    source.mkdir()
    target.mkdir()
    (source / "PG_VERSION").write_text("14\n")
    (target / "unexpected").write_text("data")
    with pytest.raises(migration.MigrationError, match="not empty"):
        migration.validate_storage_paths(
            source, target, container_pgdata="/var/lib/postgresql/18/docker"
        )
