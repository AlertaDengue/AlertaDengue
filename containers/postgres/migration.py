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


def run_command(args: Sequence[str], password: str | None = None) -> str:
    """Run a command without putting credentials in its argument list."""
    env = None if password is None else {**os.environ, "PGPASSWORD": password}
    try:
        result = subprocess.run(
            list(args), check=True, capture_output=True, text=True, env=env
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


def _pg_version_marker(path: Path) -> Path | None:
    """Find a PostgreSQL marker at a cluster path or known legacy child."""
    for candidate in (
        path / "PG_VERSION",
        path / "data" / "PG_VERSION",
        path / "pgdata" / "PG_VERSION",
    ):
        if candidate.is_file():
            return candidate
    return None


def validate_storage_paths(
    source_path: Path,
    target_path: Path,
    *,
    container_pgdata: str,
) -> None:
    """Reject unsafe source/target filesystem layouts."""
    source = _canonical_path(source_path)
    target = _canonical_path(target_path)
    if not source.is_dir():
        raise MigrationError(f"source path does not exist: {source}")
    marker = _pg_version_marker(source)
    if marker is None or marker.read_text(encoding="ascii").strip() != "14":
        raise MigrationError(
            f"source path must contain a PostgreSQL 14 PG_VERSION: {source}"
        )
    target_marker = _pg_version_marker(target) if target.exists() else None
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
    run_command(
        [
            "pg_dumpall",
            "--globals-only",
            "--no-role-passwords",
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


def dump_database(source: Endpoint, output: Path) -> None:
    """Create and verify a PostgreSQL custom-format archive."""
    output.parent.mkdir(parents=True, exist_ok=True)
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
    validate_archive(output)


def restore(target: Endpoint, globals_dump: Path, archive: Path) -> None:
    """Restore globals, then the archive, into a clean target."""
    if not globals_dump.is_file() or globals_dump.stat().st_size == 0:
        raise MigrationError(
            f"globals dump is missing or empty: {globals_dump}"
        )
    validate_archive(archive)
    restore_globals = globals_dump.with_suffix(".target.sql")
    restore_globals.write_text(
        "\n".join(
            line
            for line in globals_dump.read_text().splitlines()
            if not line.startswith("CREATE ROLE postgres;")
            and not line.startswith("ALTER ROLE postgres ")
        )
        + "\n"
    )
    run_command(
        [
            "psql",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            target.host,
            "-p",
            target.port,
            "-U",
            target.user,
            "-d",
            target.database,
            "-f",
            str(restore_globals),
        ],
        target.password,
    )
    run_command(
        [
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "-h",
            target.host,
            "-p",
            target.port,
            "-U",
            target.user,
            "-d",
            target.database,
            str(archive),
        ],
        target.password,
    )


def catalog_snapshot(endpoint: Endpoint) -> dict[str, str]:
    """Capture deterministic core catalog values."""
    queries = {
        "version": "SHOW server_version_num",
        "encoding": "SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname=current_database()",
        "schemas": "SELECT coalesce(string_agg(nspname, ',' ORDER BY nspname),'') FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname <> 'information_schema'",
        "relations": "SELECT coalesce(string_agg(n.nspname || '.' || c.relname || ':' || c.relkind::text, ',' ORDER BY n.nspname,c.relname),'') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema' AND c.relkind IN ('r','p','v','m','S')",
        "extensions": "SELECT coalesce(string_agg(extname, ' ,' ORDER BY extname), ' ') FROM pg_extension",
        "extension_versions": "SELECT coalesce(string_agg(extname || '=' || extversion, ' ,' ORDER BY extname), ' ') FROM pg_extension",
        "migration_rows": "SELECT count(*)::text FROM django_migrations",
    }
    return {key: scalar(endpoint, sql) for key, sql in queries.items()}


def validate_snapshots(source: Endpoint, target: Endpoint) -> None:
    """Fail if core source and target catalogs differ."""
    left, right = catalog_snapshot(source), catalog_snapshot(target)
    if any(
        key not in {"version", "extension_versions"}
        and left[key] != right[key]
        for key in left
    ):
        differences = {
            key: (left[key], right[key])
            for key in left
            if key not in {"version", "extension_versions"}
            and left[key] != right[key]
        }
        raise MigrationError(
            f"source/target catalog mismatch: {json.dumps(differences)}"
        )


def endpoint_from_args(args: argparse.Namespace, prefix: str) -> Endpoint:
    """Build an endpoint from parsed arguments."""
    return Endpoint(
        getattr(args, f"{prefix}_host"),
        getattr(args, f"{prefix}_port"),
        getattr(args, f"{prefix}_database"),
        getattr(args, f"{prefix}_user"),
        getattr(args, f"{prefix}_password"),
    )


def add_endpoint_arguments(
    parser: argparse.ArgumentParser, prefix: str
) -> None:
    for name in ("host", "port", "database", "user"):
        parser.add_argument(f"--{prefix}-{name}", required=True)
    parser.add_argument(f"--{prefix}-password")


def build_parser() -> argparse.ArgumentParser:
    """Build the migration CLI parser."""
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="action", required=True)
    for action in ("preflight", "dump", "restore", "validate"):
        command = sub.add_parser(action)
        add_endpoint_arguments(command, "source")
        add_endpoint_arguments(command, "target")
        command.add_argument(
            "--output-dir", type=Path, default=Path("migration-dumps")
        )
        command.add_argument("--archive", type=Path)
        command.add_argument("--globals", type=Path)
        command.add_argument(
            "--required-bytes", type=int, default=1_073_741_824
        )
        command.add_argument("--disk-path", type=Path, default=Path("."))
        command.add_argument("--source-path", type=Path)
        command.add_argument("--target-path", type=Path)
        command.add_argument(
            "--container-pgdata", default="/var/lib/postgresql/18/docker"
        )
    root.add_argument("--source-major", default="14")
    root.add_argument("--target-major", default="18")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one migration phase."""
    args = build_parser().parse_args(argv)
    source, target = (
        endpoint_from_args(args, "source"),
        endpoint_from_args(args, "target"),
    )
    try:
        validate_distinct_endpoints(source, target)
        validate_versions(
            major_from_version_num(scalar(source, "SHOW server_version_num")),
            major_from_version_num(scalar(target, "SHOW server_version_num")),
        )
        if args.action in ("preflight", "dump"):
            if args.source_path is None or args.target_path is None:
                raise MigrationError(
                    "preflight and dump require --source-path and --target-path"
                )
            validate_storage_paths(
                args.source_path,
                args.target_path,
                container_pgdata=args.container_pgdata,
            )
            validate_target_empty(target)
            validate_free_space(args.target_path, args.required_bytes)
        if args.action == "dump":
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            dump_globals(source, args.output_dir / f"globals-{stamp}.sql")
            dump_database(source, args.output_dir / f"database-{stamp}.dump")
        elif args.action == "restore":
            if args.globals is None or args.archive is None:
                raise MigrationError(
                    "restore requires --globals and --archive"
                )
            validate_target_empty(target)
            restore(target, args.globals, args.archive)
        elif args.action == "validate":
            validate_snapshots(source, target)
        print(f"{args.action}: PASS")
        return 0
    except MigrationError as exc:
        print(f"migration refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
