"""Exercise archive validation without starting PostgreSQL."""

import json
import os
import subprocess
from pathlib import Path

import pytest


ENTRYPOINT = Path(__file__).parents[1] / "containers/postgres/scripts/entrypoint.sh"
ROOT = ENTRYPOINT.parents[3]


@pytest.mark.parametrize(
    ("mode", "config_kind", "succeeds"),
    [
        ("off", "missing", True),
        ("off", "directory", True),
        ("on", "missing", False),
        ("on", "directory", False),
        ("on", "file", True),
        ("always", "file", True),
        ("invalid", "file", False),
    ],
)
def test_archive_config_validation(
    tmp_path: Path, mode: str, config_kind: str, succeeds: bool
) -> None:
    config = tmp_path / "pgbackrest.conf"
    if config_kind == "directory":
        config.mkdir()
    elif config_kind == "file":
        config.write_text("[global]\n", encoding="utf-8")

    pgdata = tmp_path / "postgresql" / "18" / "docker"
    pgdata.mkdir(parents=True)
    (pgdata / "PG_VERSION").write_text("18\n", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("mkdir", "docker-entrypoint.sh"):
        command = bin_dir / name
        command.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        command.chmod(0o755)

    result = subprocess.run(
        ["bash", str(ENTRYPOINT), "postgres"],
        env={
            **os.environ,
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "PGDATA": str(pgdata),
            "PGBACKREST_CONFIG": str(config),
            "PG_ARCHIVE_MODE": mode,
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert (result.returncode == 0) is succeeds, result.stderr
    if not succeeds:
        expected_error = (
            "Invalid PG_ARCHIVE_MODE" if mode == "invalid" else "pgBackRest config"
        )
        assert expected_error in result.stderr


@pytest.mark.parametrize("profile", ["dev", "staging", "prod"])
def test_compose_archive_mode_and_config_mount(profile: str) -> None:
    environment = os.environ.copy()
    environment.pop("PG_ARCHIVE_MODE", None)
    environment.update(
        ENV=profile,
        PG18_POSTGRES_IMAGE="alertadengue-postgres:18.6-bookworm",
        PG18_HOST_PGDATA="/tmp/pg18-compose-test",
        PSQL_PASSWORD="render-only",
        PSQL_DB="db",
        PSQL_USER="user",
        PSQL_PORT="55432",
        PSQL_HOST_PORT="55433",
    )
    command = [
        "docker", "compose", "--env-file", ".envs/.env",
        "-f", "containers/compose-base.yaml",
        "-f", f"containers/compose-{profile}.yaml",
    ]
    if profile != "dev":
        command.extend(["-f", "containers/compose-pgbackrest.yaml"])
    result = subprocess.run(
        [*command, "config", "--format", "json"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )
    postgres = json.loads(result.stdout)["services"]["postgres"]
    assert postgres["environment"]["PG_ARCHIVE_MODE"] == (
        "off" if profile == "dev" else "on"
    )
    config_mounts = [
        volume
        for volume in postgres["volumes"]
        if volume["target"] == "/etc/pgbackrest/pgbackrest.conf"
    ]
    assert bool(config_mounts) is (profile != "dev")


def test_development_can_enable_archiving_explicitly() -> None:
    environment = {
        **os.environ,
        "ENV": "dev",
        "PG_ARCHIVE_MODE": "on",
        "PG18_POSTGRES_IMAGE": "alertadengue-postgres:18.6-bookworm",
        "PG18_HOST_PGDATA": "/tmp/pg18-compose-test",
        "PSQL_PASSWORD": "render-only",
        "PSQL_DB": "db",
        "PSQL_USER": "user",
        "PSQL_PORT": "55432",
    }
    result = subprocess.run(
        [
            "docker", "compose", "--env-file", ".envs/.env",
            "-f", "containers/compose-base.yaml",
            "-f", "containers/compose-dev.yaml",
            "-f", "containers/compose-pgbackrest.yaml",
            "config", "--format", "json",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=True,
    )
    postgres = json.loads(result.stdout)["services"]["postgres"]
    assert postgres["environment"]["PG_ARCHIVE_MODE"] == "on"
    assert any(
        volume["target"] == "/etc/pgbackrest/pgbackrest.conf"
        for volume in postgres["volumes"]
    )
