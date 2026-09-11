#!/usr/bin/env python3
"""Guarded PostgreSQL 14-to-18 logical migration workflow."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Sequence


class MigrationError(RuntimeError):
    """A migration safety gate failed."""


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: str
    database: str
    user: str
    password: str | None = None


def _psql_args(endpoint: Endpoint, sql: str) -> list[str]:
    return [
        "psql",
        "-X",
        "-A",
        "-t",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        endpoint.host,
        "-p",
        endpoint.port,
        "-U",
        endpoint.user,
        "-d",
        endpoint.database,
        "-c",
        sql,
    ]


def run_command(
    args: Sequence[str],
    password: str | None = None,
    input_text: str | None = None,
) -> str:
    """Run a command without putting credentials in its argument list."""
    env = None if password is None else {**os.environ, "PGPASSWORD": password}
    try:
        result = subprocess.run(
            list(args),
            check=True,
            capture_output=True,
            text=True,
            env=env,
            input=input_text,
        )
    except subprocess.CalledProcessError as exc:
        raise MigrationError(
            f"command failed with exit code {exc.returncode}: "
            f"{args[0]} (credentials omitted)"
        ) from exc
    return result.stdout


def scalar(endpoint: Endpoint, sql: str) -> str:
    """Return one scalar query result."""
    return run_command(_psql_args(endpoint, sql), endpoint.password).strip()


def major_from_version_num(value: str) -> str:
    """Convert PostgreSQL server_version_num to its major component."""
    return str(int(value) // 10000)


def validate_versions(source: str, target: str) -> None:
    """Require PostgreSQL 14 as source and PostgreSQL 18 as target."""

    def major(value: str) -> str:
        text = str(value).strip()
        return text if text in {"14", "18"} else text.split(".", 1)[0]

    if major(source) != "14":
        raise MigrationError(f"source major must be 14, got {source!r}")
    if major(target) != "18":
        raise MigrationError(f"target major must be 18, got {target!r}")


def validate_distinct_endpoints(source: Endpoint, target: Endpoint) -> None:
    """Reject endpoints identifying the same database."""
    if (source.host, source.port, source.database) == (
        target.host,
        target.port,
        target.database,
    ):
        raise MigrationError("source and target endpoints must be different")


def validate_target_empty(target: Endpoint) -> None:
    """Reject a target containing user-owned relations."""
    sql = """
    SELECT count(*) FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
    """
    objects = int(scalar(target, sql))
    if objects:
        raise MigrationError(
            f"target database is not empty ({objects} user objects); "
            "refusing automatic replacement"
        )


def validate_free_space(path: Path, required_bytes: int) -> None:
    """Require enough free space for dump and restore artifacts."""
    free = shutil.disk_usage(path).free
    if free < required_bytes:
        raise MigrationError(
            f"insufficient free space at {path}: {free} < {required_bytes}"
        )


def _canonical_path(path: Path) -> Path:
    """Resolve a path without requiring a not-yet-created target."""
    return path.expanduser().resolve(strict=False)


def _pg_version_marker(path: Path, *, major: str) -> Path | None:
    """Find the exact marker for the host volume layout."""
    candidate = (
        path / "PG_VERSION"
        if major == "14"
        else path / "18" / "docker" / "PG_VERSION"
    )
    return candidate if candidate.is_file() else None


def validate_storage_paths(
    source_path: Path,
    target_path: Path,
    *,
    container_pgdata: str,
    mode: str = "cutover",
) -> None:
    """Reject unsafe source/target filesystem layouts."""
    if mode not in {"initialization", "cutover", "restore-validation", "steady-state"}:
        raise MigrationError(f"unsupported preflight mode: {mode}")
    source = _canonical_path(source_path)
    target = _canonical_path(target_path)
    if mode == "initialization":
        if not target.is_dir() or any(target.iterdir()):
            raise MigrationError(
                "initialization requires an existing empty PG18_HOST_PGDATA parent"
            )
        return
    if mode in {"restore-validation", "steady-state"}:
        marker = (
            _pg_version_marker(target, major="18") if target.is_dir() else None
        )
        if (
            marker is None
            or marker.read_text(encoding="ascii").strip() != "18"
        ):
            raise MigrationError(
                f"{mode} requires PG18_HOST_PGDATA/18/docker/PG_VERSION = 18"
            )
        return
    if not source.is_dir():
        raise MigrationError(f"source path does not exist: {source}")
    marker = _pg_version_marker(source, major="14")
    if marker is None or marker.read_text(encoding="ascii").strip() != "14":
        raise MigrationError(
            f"source path must contain a PostgreSQL 14 PG_VERSION: {source}"
        )
    target_marker = (
        _pg_version_marker(target, major="18") if target.exists() else None
    )
    if (target / "PG_VERSION").is_file():
        raise MigrationError(
            "PG18_HOST_PGDATA/PG_VERSION is not a valid PG18 marker"
        )
    if (
        target_marker is not None
        and target_marker.read_text(encoding="ascii").strip() != "18"
    ):
        raise MigrationError(
            f"target path contains a non-PostgreSQL-18 PG_VERSION: {target}"
        )
    if target.exists() and target_marker is None and any(target.iterdir()):
        raise MigrationError(f"target path is not empty: {target}")
    try:
        common = Path(os.path.commonpath((source, target)))
    except ValueError as exc:
        raise MigrationError(
            "source and target paths use different roots"
        ) from exc
    if common == source or common == target:
        raise MigrationError(
            "source and target paths must be separate sibling directories"
        )
    if container_pgdata != "/var/lib/postgresql/18/docker":
        raise MigrationError(
            "target container PGDATA must be /var/lib/postgresql/18/docker"
        )


def validate_archive(path: Path) -> None:
    """Require a nonempty archive readable by pg_restore."""
    if not path.is_file() or path.stat().st_size == 0:
        raise MigrationError(f"dump archive is missing or empty: {path}")
    run_command(["pg_restore", "--list", str(path)])


def dump_globals(source: Endpoint, output: Path) -> None:
    """Dump global roles and objects."""
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.close(descriptor)
    run_command(
        [
            "pg_dumpall",
            "--globals-only",
            "-h",
            source.host,
            "-p",
            source.port,
            "-U",
            source.user,
            "-f",
            str(output),
        ],
        source.password,
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise MigrationError(f"globals dump is missing or empty: {output}")
    output.chmod(0o600)


def dump_database(source: Endpoint, output: Path) -> None:
    """Create and verify a PostgreSQL custom-format archive."""
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.close(descriptor)
    run_command(
        [
            "pg_dump",
            "--format=custom",
            "--compress=9",
            "--quote-all-identifiers",
            "--verbose",
            "-h",
            source.host,
            "-p",
            source.port,
            "-U",
            source.user,
            "--file",
            str(output),
            source.database,
        ],
        source.password,
    )
    output.chmod(0o600)
    validate_archive(output)



def restore(target: Endpoint, globals_file: Path, archive: Path) -> None:
    """Restore reviewed globals and the custom archive with fail-fast clients."""
    if not globals_file.is_file() or globals_file.stat().st_size == 0:
        raise MigrationError("globals dump is missing or empty")
    run_command(["psql", "-X", "-v", "ON_ERROR_STOP=1", "-h", target.host, "-p", target.port, "-U", target.user, "-d", "postgres", "--file", str(globals_file)], target.password)
    validate_archive(archive)
    run_command(["pg_restore", "--exit-on-error", "--single-transaction", "-h", target.host, "-p", target.port, "-U", target.user, "-d", target.database, str(archive)], target.password)


def validate_contract(source: Endpoint, target: Endpoint) -> None:
    """Check versions, extensions, schema and Django migration records."""
    validate_versions(major_from_version_num(scalar(source, "SHOW server_version_num")), major_from_version_num(scalar(target, "SHOW server_version_num")))
    extensions = set(filter(None, scalar(target, "SELECT string_agg(extname, ',') FROM pg_extension").split(",")))
    missing = {"postgis", "hstore", "plpython3u", "postgres_fdw"} - extensions
    if missing:
        raise MigrationError(f"target is missing required extensions: {', '.join(sorted(missing))}")
    if int(scalar(target, "SELECT count(*) FROM django_migrations")) < 1:
        raise MigrationError("target has no Django migration records")


def add_endpoint_arguments(parser: argparse.ArgumentParser, prefix: str) -> None:
    for name in ("host", "port", "database", "user"):
        parser.add_argument(f"--{prefix}-{name}", required=True)
    parser.add_argument(f"--{prefix}-password")


def endpoint_from_args(args: argparse.Namespace, prefix: str) -> Endpoint:
    return Endpoint(*(getattr(args, f"{prefix}_{name}") for name in ("host", "port", "database", "user", "password")))


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="PostgreSQL 14 to 18 logical migration")
    sub = root.add_subparsers(dest="action", required=True)
    for action in ("preflight", "dump", "restore", "validate"):
        command = sub.add_parser(action)
        add_endpoint_arguments(command, "source")
        add_endpoint_arguments(command, "target")
        command.add_argument("--source-path", type=Path, required=True)
        command.add_argument("--target-path", type=Path, required=True)
        command.add_argument("--disk-path", type=Path, default=Path("."))
        command.add_argument("--required-bytes", type=int, default=1_073_741_824)
        command.add_argument("--output-dir", type=Path)
        command.add_argument("--globals", dest="globals_file", type=Path)
        command.add_argument("--archive", type=Path)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source, target = endpoint_from_args(args, "source"), endpoint_from_args(args, "target")
        validate_storage_paths(args.source_path, args.target_path, container_pgdata="/var/lib/postgresql/18/docker")
        validate_free_space(args.disk_path, args.required_bytes)
        if args.action == "preflight":
            validate_versions(major_from_version_num(scalar(source, "SHOW server_version_num")), major_from_version_num(scalar(target, "SHOW server_version_num")))
        elif args.action == "dump":
            if args.output_dir is None:
                raise MigrationError("dump requires --output-dir")
            dump_globals(source, args.output_dir / "globals.sql")
            dump_database(source, args.output_dir / "database.dump")
        elif args.action == "restore":
            if args.globals_file is None or args.archive is None:
                raise MigrationError("restore requires --globals and --archive")
            restore(target, args.globals_file, args.archive)
        else:
            validate_contract(source, target)
        print(f"{args.action}: PASS")
        return 0
    except MigrationError as exc:
        print(f"migration refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
