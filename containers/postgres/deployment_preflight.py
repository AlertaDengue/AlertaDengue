from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Literal


class PreflightError(ValueError):
    pass


def _canonical(path: str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _read_marker(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="ascii").strip()


def _cluster_system_identifier(target: Path, postgres_image: str) -> str:
    if not postgres_image:
        raise PreflightError("PG18 PostgreSQL image is required for system identifier inspection")
    try:
        result = subprocess.run(
            [
                "docker", "run", "--rm", "--network=none",
                "--read-only", "--entrypoint", "pg_controldata",
                "--env", "LC_ALL=C", "--mount",
                f"type=bind,source={target},target=/var/lib/postgresql,readonly",
                postgres_image,
                "/var/lib/postgresql/18/docker",
            ],

            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PreflightError(
            "cannot inspect PG18 cluster system identifier"
        ) from exc
    for line in result.stdout.splitlines():
        if line.startswith("Database system identifier"):
            return line.split(":", 1)[1].strip()
    raise PreflightError("PG18 cluster system identifier is unavailable")


def _pg14_marker(path: Path) -> str | None:
    return _read_marker(path / "PG_VERSION")


def _pg18_marker(path: Path) -> str | None:
    """Return only the marker for PGDATA=/var/lib/postgresql/18/docker."""
    return _read_marker(path / "18" / "docker" / "PG_VERSION")


PreflightMode = Literal[
    "initialization", "cutover", "restore-validation", "steady-state"
]


def validate_deployment_paths(
    source_raw: str,
    target_raw: str,
    *,
    mode: PreflightMode = "cutover",
    state_file: Path | None = None,
    require_validated_state: bool = False,
    postgres_image: str | None = None,
) -> tuple[Path | None, Path]:
    if mode not in {
        "initialization",
        "cutover",
        "restore-validation",
        "steady-state",
    }:
        raise PreflightError(f"unsupported preflight mode: {mode}")
    if mode == "cutover" and (not source_raw or not source_raw.strip()):
        raise PreflightError("PG14_HOST_PGDATA is required")
    if not target_raw or not target_raw.strip():
        raise PreflightError("PG18_HOST_PGDATA is required")
    source = (
        _canonical(source_raw) if source_raw and source_raw.strip() else None
    )
    target = _canonical(target_raw)
    if mode == "steady-state" and not target_raw.strip():
        raise PreflightError("PG18_HOST_PGDATA is required")
    if source is not None and source == target:
        raise PreflightError(
            "PG18_HOST_PGDATA must differ from PG14_HOST_PGDATA"
        )
    try:
        common = (
            Path(os.path.commonpath((source, target)))
            if source is not None
            else None
        )
    except ValueError as exc:
        raise PreflightError(
            "PG14_HOST_PGDATA and PG18_HOST_PGDATA are incompatible paths"
        ) from exc
    if source is not None and common in (source, target):
        raise PreflightError(
            "PG14_HOST_PGDATA and PG18_HOST_PGDATA must be sibling paths, not nested"
        )
    if not target.is_dir():
        raise PreflightError(f"validated PG18 target is unavailable: {target}")
    target_marker = _pg18_marker(target)
    if mode == "steady-state" and require_validated_state:
        if state_file is None or not state_file.is_file():
            raise PreflightError(
                "steady-state requires validated migration state"
            )
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PreflightError(
                "steady-state validation state is invalid"
            ) from exc
        if (
            state.get("state") != "validated"
            or state.get("target_path") != str(target)
            or state.get("postgres_major") != "18"
            or not state.get("system_identifier")
        ):
            raise PreflightError(
                "steady-state validation state does not match target"
            )
        if state["system_identifier"] != _cluster_system_identifier(target, postgres_image or ""):
            raise PreflightError(
                "steady-state validation state belongs to another cluster"
            )
    if mode == "initialization":
        if any(target.iterdir()):
            raise PreflightError(
                "initialization requires an empty PG18_HOST_PGDATA parent"
            )
        return source, target
    if mode in {"restore-validation", "steady-state"}:
        if target_marker != "18":
            raise PreflightError(
                f"{mode} requires PG18_HOST_PGDATA/18/docker/PG_VERSION = 18"
            )
        return source, target
    if source is None or not source.is_dir():
        raise PreflightError(f"PG14_HOST_PGDATA does not exist: {source}")
    source_marker = _pg14_marker(source)
    if source_marker != "14":
        raise PreflightError(
            f"PG14_HOST_PGDATA must contain PostgreSQL 14 PG_VERSION, got {source_marker!r}"
        )
    if (target / "PG_VERSION").is_file():
        raise PreflightError(
            "PG18_HOST_PGDATA contains non-PostgreSQL-18 marker at PG18_HOST_PGDATA/PG_VERSION"
        )
    if target_marker is not None and target_marker != "18":
        raise PreflightError(
            f"PG18_HOST_PGDATA contains non-PostgreSQL-18 PG_VERSION: {target_marker!r}"
        )
    if target_marker is None and any(target.iterdir()):
        raise PreflightError(
            "PG18_HOST_PGDATA is neither an empty directory nor a PostgreSQL 18 cluster"
        )
    return source, target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate PostgreSQL deployment storage before startup"
    )
    parser.add_argument(
        "--source", default=os.environ.get("PG14_HOST_PGDATA", "")
    )
    parser.add_argument(
        "--target", default=os.environ.get("PG18_HOST_PGDATA", "")
    )
    parser.add_argument("--state-file", type=Path)
    parser.add_argument(
        "--postgres-image", default=os.environ.get("PG18_POSTGRES_IMAGE", "")
    )
    parser.add_argument("--require-validated-state", action="store_true")
    parser.add_argument(
        "--mode",
        choices=(
            "initialization",
            "cutover",
            "restore-validation",
            "steady-state",
        ),
        default="cutover",
    )
    args = parser.parse_args()
    try:
        source, target = validate_deployment_paths(
            args.source,
            args.target,
            mode=args.mode,
            state_file=args.state_file,
            require_validated_state=args.require_validated_state,
            postgres_image=args.postgres_image,
        )
    except PreflightError as exc:
        print(f"[EE] {exc}")
        return 2
    print(f"PG14_HOST_PGDATA_CANON={source}")
    print(f"PG18_HOST_PGDATA_CANON={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
