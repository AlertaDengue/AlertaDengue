import importlib.util
import sys

import pytest

SPEC = importlib.util.spec_from_file_location("postgres_migration", "containers/postgres/migration.py")
migration = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["postgres_migration"] = migration
SPEC.loader.exec_module(migration)


def endpoint(host="source"):
    return migration.Endpoint(host, "5432", "db", "operator", "secret")


def paths(tmp_path):
    source, target = tmp_path / "pg14", tmp_path / "pg18"
    source.mkdir()
    target.mkdir()
    (source / "PG_VERSION").write_text("14\n", encoding="ascii")
    return source, target


def test_paths_require_separate_absolute_pg14_source_and_empty_target(tmp_path):
    source, target = paths(tmp_path)
    migration.validate_storage_paths(source, target, container_pgdata="/var/lib/postgresql/18/docker")
    (target / "file").write_text("x", encoding="ascii")
    with pytest.raises(migration.MigrationError, match="not empty"):
        migration.validate_storage_paths(source, target, container_pgdata="/var/lib/postgresql/18/docker")
    with pytest.raises(migration.MigrationError, match="sibling"):
        migration.validate_storage_paths(source, source / "nested", container_pgdata="/var/lib/postgresql/18/docker")


def test_source_marker_and_credentials_are_guarded(monkeypatch, tmp_path):
    source, target = paths(tmp_path)
    (source / "PG_VERSION").write_text("13\n", encoding="ascii")
    with pytest.raises(migration.MigrationError, match="14"):
        migration.validate_storage_paths(source, target, container_pgdata="/var/lib/postgresql/18/docker")
    seen = []
    monkeypatch.setattr(migration.subprocess, "run", lambda args, **kwargs: seen.append(args) or type("R", (), {"stdout": ""})())
    migration.run_command(["psql", "-U", "operator"], "secret")
    assert "secret" not in seen[0]


def test_dumps_are_private_and_failures_stop(monkeypatch, tmp_path):
    output = tmp_path / "globals.sql"
    calls = []
    monkeypatch.setattr(migration, "run_command", lambda args, *rest: calls.append(args) or output.write_text("dump", encoding="ascii") or "")
    migration.dump_globals(endpoint(), output)
    assert output.stat().st_mode & 0o777 == 0o600
    assert "pg_dumpall" in calls[0]
    archive = tmp_path / "archive.dump"
    archive.write_bytes(b"x")
    monkeypatch.setattr(migration, "validate_archive", lambda _: None)
    monkeypatch.setattr(migration, "run_command", lambda *args: (_ for _ in ()).throw(migration.MigrationError("stop")))
    with pytest.raises(migration.MigrationError, match="stop"):
        migration.restore(endpoint("target"), output, archive)
