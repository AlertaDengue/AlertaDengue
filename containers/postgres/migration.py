#!/usr/bin/env python3
"""Operator-driven PostgreSQL 14-to-18 logical migration checks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Sequence


class MigrationError(RuntimeError):
    """A migration safety gate failed."""


@dataclass(frozen=True)
class Endpoint:
    """Connection settings; passwords are passed only through the environment."""

    host: str
    port: str
    database: str
    user: str
    password: str | None = None


APPLICATION_SCHEMAS = {
    "public",
    "Dengue_global",
    "Municipio",
    "ingestion",
    "episcanner",
    "vegetation_indices",
    "weather",
}
CRITICAL_RELATIONS = (
    '"Dengue_global"."Municipio"',
    '"Municipio"."Historico_alerta"',
    '"Municipio"."Historico_alerta_chik"',
    '"Municipio"."Historico_alerta_zika"',
    '"Municipio"."Notificacao"',
)


def _psql_args(endpoint: Endpoint, sql: str) -> list[str]:
    return [
        "psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-h",
        endpoint.host, "-p", endpoint.port, "-U", endpoint.user, "-d",
        endpoint.database, "-c", sql,
    ]


def run_command(args: Sequence[str], password: str | None = None) -> str:
    """Run a command without placing credentials in its argument vector."""
    env = None if password is None else {**os.environ, "PGPASSWORD": password}
    try:
        completed = subprocess.run(
            list(args), check=True, capture_output=True, text=True, env=env
        )
    except subprocess.CalledProcessError as exc:
        raise MigrationError(
            f"command failed with exit code {exc.returncode}: {args[0]} "
            "(credentials omitted)"
        ) from exc
    return completed.stdout


def scalar(endpoint: Endpoint, sql: str) -> str:
    """Return a scalar query result."""
    return run_command(_psql_args(endpoint, sql), endpoint.password).strip()


def major_from_version_num(value: str) -> str:
    """Convert ``server_version_num`` to its major component."""
    return str(int(value) // 10000)


def validate_versions(source: str, target: str) -> None:
    """Require PostgreSQL 14 as source and PostgreSQL 18 as target."""
    if source.split(".", 1)[0] != "14":
        raise MigrationError(f"source major must be 14, got {source!r}")
    if target.split(".", 1)[0] != "18":
        raise MigrationError(f"target major must be 18, got {target!r}")


def validate_distinct_endpoints(source: Endpoint, target: Endpoint) -> None:
    """Reject endpoints identifying the same database."""
    if (source.host, source.port, source.database) == (
        target.host, target.port, target.database
    ):
        raise MigrationError("source and target endpoints must be different")


def validate_target_empty(target: Endpoint) -> None:
    """Reject a target database with user relations of any restorable class."""
    sql = """
        SELECT count(*) FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
          AND n.nspname NOT LIKE 'pg_toast%'
          AND n.nspname NOT LIKE 'pg_temp_%'
          AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
    """
    objects = int(scalar(target, sql))
    if objects:
        raise MigrationError(f"target database is not empty ({objects} user objects)")


def validate_free_space(path: Path, required_bytes: int) -> None:
    """Require enough free space for dump and restore artifacts."""
    if not path.is_dir():
        raise MigrationError(f"dump filesystem does not exist: {path}")
    free = shutil.disk_usage(path).free
    if free < required_bytes:
        raise MigrationError(
            f"insufficient free space at {path}: {free} < {required_bytes}"
        )


def validate_storage_paths(source_path: Path, target_path: Path) -> None:
    """Require distinct absolute PG14 source and empty PG18 target paths."""
    if not source_path.is_absolute() or not target_path.is_absolute():
        raise MigrationError("source and target paths must be absolute")
    source = source_path.resolve(strict=False)
    target = target_path.resolve(strict=False)
    if not source.is_dir():
        raise MigrationError(f"source path does not exist: {source}")
    marker = source / "PG_VERSION"
    if not marker.is_file() or marker.read_text(encoding="ascii").strip() != "14":
        raise MigrationError(f"source path must contain PG_VERSION=14: {source}")
    if not target.is_dir():
        raise MigrationError(f"target path does not exist: {target}")
    if any(target.iterdir()):
        raise MigrationError(f"target path is not empty: {target}")
    try:
        common = Path(os.path.commonpath((source, target)))
    except ValueError as exc:
        raise MigrationError("source and target paths use different roots") from exc
    if common in {source, target}:
        raise MigrationError("source and target paths must be separate siblings")


def validate_client_commands() -> None:
    """Check commands needed by the four operator actions."""
    missing = [
        name for name in ("psql", "pg_dump", "pg_restore") if not shutil.which(name)
    ]
    if missing:
        raise MigrationError(
            f"required PostgreSQL client command is unavailable: {missing[0]}"
        )


def prepare_output_directory(path: Path) -> None:
    """Create a new private dump directory; never reuse an existing target."""
    if path.exists():
        raise MigrationError(f"dump output directory already exists: {path}")
    path.mkdir(mode=0o700, parents=True)


def validate_archive(path: Path) -> None:
    """Require a nonempty archive readable by pg_restore."""
    if not path.is_file() or path.stat().st_size == 0:
        raise MigrationError(f"dump archive is missing or empty: {path}")
    run_command(["pg_restore", "--list", str(path)])


def dump_database(source: Endpoint, output: Path) -> None:
    """Create a mode-0600 custom archive and verify it immediately."""
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    run_command(
        [
            "pg_dump", "--format=custom", "--compress=9",
            "--quote-all-identifiers", "-h", source.host, "-p", source.port,
            "-U", source.user, "--file", str(output), source.database,
        ],
        source.password,
    )
    output.chmod(0o600)
    validate_archive(output)


def restore(target: Endpoint, archive: Path) -> None:
    """Restore only application objects into the pre-created target database."""
    target_major = major_from_version_num(scalar(target, "SHOW server_version_num"))
    if target_major != "18":
        raise MigrationError(f"target major must be 18, got {target_major!r}")
    validate_target_empty(target)
    validate_archive(archive)
    run_command(
        [
            "pg_restore", "--exit-on-error", "--single-transaction",
            "--no-owner", "--no-acl", f"--role={target.user}", "-h",
            target.host, "-p", target.port, "-U", target.user, "-d",
            target.database, str(archive),
        ],
        target.password,
    )


def validate_sequences(target: Endpoint) -> None:
    """Ensure owned serial and identity sequences are not behind table IDs."""
    rows = scalar(
        target,
        """
        SELECT n.nspname || chr(9) || c.relname || chr(9) || a.attname
        FROM pg_class sequence
        JOIN pg_depend dependency ON dependency.objid = sequence.oid
        JOIN pg_class c ON c.oid = dependency.refobjid
        JOIN pg_attribute a ON a.attrelid = c.oid
          AND a.attnum = dependency.refobjsubid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE sequence.relkind = 'S' AND dependency.deptype IN ('a', 'i')
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        """,
    )
    for row in filter(None, rows.splitlines()):
        schema, table, column = row.split("\t")
        quoted = lambda value: '"' + value.replace('"', '""') + '"'
        relation = f"{quoted(schema)}.{quoted(table)}"
        sequence = scalar(target, f"SELECT pg_get_serial_sequence('{relation}', '{column}')")
        if not sequence:
            continue
        last_value = int(scalar(target, f"SELECT last_value FROM {sequence}"))
        maximum = int(scalar(target, f"SELECT coalesce(max({quoted(column)}), 0) FROM {relation}"))
        if last_value < maximum:
            raise MigrationError(f"sequence {sequence} is behind {relation}.{column}")


def validate_contract(source: Endpoint, target: Endpoint) -> None:
    """Check the small application contract required before cutover."""
    validate_distinct_endpoints(source, target)
    validate_versions(
        major_from_version_num(scalar(source, "SHOW server_version_num")),
        major_from_version_num(scalar(target, "SHOW server_version_num")),
    )
    extensions = set(
        filter(
            None,
            scalar(
                target, "SELECT string_agg(extname, ',') FROM pg_extension"
            ).split(","),
        )
    )
    required = {"postgis", "hstore", "plpython3u", "postgres_fdw"}
    if missing := required - extensions:
        raise MigrationError(
            f"target is missing required extensions: {', '.join(sorted(missing))}"
        )
    schemas = set(
        filter(
            None,
            scalar(
                target, "SELECT string_agg(nspname, ',') FROM pg_namespace"
            ).split(","),
        )
    )
    if missing := APPLICATION_SCHEMAS - schemas:
        raise MigrationError(
            f"target is missing required schemas: {', '.join(sorted(missing))}"
        )
    if scalar(target, "SELECT to_regclass('public.django_migrations') IS NOT NULL") != "t":
        raise MigrationError("target is missing django_migrations")
    if int(scalar(target, "SELECT count(*) FROM django_migrations")) < 1:
        raise MigrationError("target has no Django migration records")
    for relation in CRITICAL_RELATIONS:
        if scalar(target, f"SELECT to_regclass('{relation}') IS NOT NULL") != "t":
            raise MigrationError(f"target is missing critical relation {relation}")
    for relation in CRITICAL_RELATIONS[1:4]:
        schema, table = relation.replace('"', "").split(".")
        query = (
            "SELECT count(*) FROM information_schema.columns "
            f"WHERE table_schema = '{schema}' AND table_name = '{table}' "
            "AND column_name = 'tweet'"
        )
        if scalar(target, query) != "0":
            raise MigrationError(f"retired tweet column remains in {relation}")
    validate_sequences(target)


def add_endpoint_arguments(parser: argparse.ArgumentParser, prefix: str) -> None:
    """Add one endpoint without exposing passwords in commands."""
    for name in ("host", "port", "database", "user"):
        parser.add_argument(f"--{prefix}-{name}", required=True)
    parser.add_argument(f"--{prefix}-password")


def endpoint_from_args(args: argparse.Namespace, prefix: str) -> Endpoint:
    """Build an endpoint from one command's arguments."""
    return Endpoint(
        *(getattr(args, f"{prefix}_{name}") for name in (
            "host", "port", "database", "user", "password"
        ))
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the four-action command-line interface."""
    root = argparse.ArgumentParser(description="PostgreSQL 14 to 18 logical migration")
    commands = root.add_subparsers(dest="action", required=True)
    preflight = commands.add_parser("preflight")
    add_endpoint_arguments(preflight, "source")
    preflight.add_argument("--source-path", type=Path, required=True)
    preflight.add_argument("--target-path", type=Path, required=True)
    preflight.add_argument("--disk-path", type=Path, required=True)
    preflight.add_argument("--required-bytes", type=int, required=True)
    dump = commands.add_parser("dump")
    add_endpoint_arguments(dump, "source")
    dump.add_argument("--output-dir", type=Path, required=True)
    restore_command = commands.add_parser("restore")
    add_endpoint_arguments(restore_command, "target")
    restore_command.add_argument("--archive", type=Path, required=True)
    validate = commands.add_parser("validate")
    add_endpoint_arguments(validate, "source")
    add_endpoint_arguments(validate, "target")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    """Execute a single explicit migration operation."""
    args = build_parser().parse_args(argv)
    try:
        if args.action == "preflight":
            validate_client_commands()
            source = endpoint_from_args(args, "source")
            source_major = major_from_version_num(
                scalar(source, "SHOW server_version_num")
            )
            if source_major != "14":
                raise MigrationError(f"source major must be 14, got {source_major!r}")
            validate_storage_paths(args.source_path, args.target_path)
            validate_free_space(args.disk_path, args.required_bytes)
        elif args.action == "dump":
            prepare_output_directory(args.output_dir)
            dump_database(
                endpoint_from_args(args, "source"), args.output_dir / "database.dump"
            )
        elif args.action == "restore":
            restore(endpoint_from_args(args, "target"), args.archive)
        else:
            validate_contract(
                endpoint_from_args(args, "source"), endpoint_from_args(args, "target")
            )
        print(f"{args.action}: PASS")
        return 0
    except MigrationError as exc:
        print(f"migration refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
