from __future__ import annotations

import stat
from pathlib import Path

import pytest

from containers.pgbackrest.render_config import (
    atomic_write,
    render_template,
    validate_pg_user,
    validate_repo_path,
    validate_stanza,
)


TEMPLATE = """[global]
repo1-path=<repository path>
log-path=/var/log/pgbackrest
spool-path=/var/lib/pgbackrest/spool
lock-path=/var/lib/pgbackrest/spool
repo1-retention-full=<retention count>
repo1-retention-full-type=count
start-fast=y
process-max=<process count>

[<stanza>]
pg1-path=/var/lib/postgresql/data
pg1-socket-path=/var/run/postgresql
pg1-user=<PSQL_USER>
"""


def test_render_staging_config() -> None:
    rendered = render_template(
        TEMPLATE,
        stanza="staging",
        repo_path=Path("/var/lib/pgbackrest"),
        pg_user="dengueadmin",
        retention_full=2,
        process_max=2,
    )

    assert "[staging]" in rendered
    assert "repo1-path=/var/lib/pgbackrest" in rendered
    assert "pg1-user=dengueadmin" in rendered


def test_render_prod_config() -> None:
    rendered = render_template(
        TEMPLATE,
        stanza="prod",
        repo_path=Path("/var/lib/pgbackrest"),
        pg_user="dengueadmin",
        retention_full=3,
        process_max=4,
    )

    assert "[prod]" in rendered
    assert "repo1-retention-full=3" in rendered
    assert "process-max=4" in rendered


def test_render_restore_config() -> None:
    rendered = render_template(
        TEMPLATE,
        stanza="prod",
        repo_path=Path("/var/lib/pgbackrest-source"),
        pg_user="dengueadmin",
        retention_full=2,
        process_max=4,
    )

    assert "repo1-path=/var/lib/pgbackrest-source" in rendered
    assert "[prod]" in rendered


def test_invalid_stanza_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid stanza name"):
        validate_stanza("prod/staging")


def test_empty_user_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        validate_pg_user("   ")


def test_relative_repo_path_rejected() -> None:
    with pytest.raises(ValueError, match="must be absolute"):
        validate_repo_path(Path("relative/repo"))


def test_output_ends_with_newline() -> None:
    rendered = render_template(
        TEMPLATE.rstrip("\n"),
        stanza="staging",
        repo_path=Path("/var/lib/pgbackrest"),
        pg_user="dengueadmin",
        retention_full=2,
        process_max=2,
    )

    assert rendered.endswith("\n")


def test_atomic_write_sets_file_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "nested" / "pgbackrest.conf"
    atomic_write(output_path, "test\n")

    file_mode = stat.S_IMODE(output_path.stat().st_mode)
    assert file_mode == 0o640
