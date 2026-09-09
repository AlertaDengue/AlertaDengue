from __future__ import annotations

import argparse
import os
from pathlib import Path


class PreflightError(ValueError):
    pass


def _canonical(path: str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _marker(path: Path, *, allow_nested: bool) -> str | None:
    candidates = [path / "PG_VERSION"]
    if allow_nested:
        candidates.extend(
            path / child / "PG_VERSION" for child in ("data", "pgdata")
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip()
    return None


def validate_deployment_paths(
    source_raw: str, target_raw: str
) -> tuple[Path, Path]:
    if not source_raw or not source_raw.strip():
        raise PreflightError("PG14_HOST_PGDATA is required")
    if not target_raw or not target_raw.strip():
        raise PreflightError("PG18_HOST_PGDATA is required")
    source = _canonical(source_raw)
    target = _canonical(target_raw)
    if source == target:
        raise PreflightError(
            "PG18_HOST_PGDATA must differ from PG14_HOST_PGDATA"
        )
    try:
        common = Path(os.path.commonpath((source, target)))
    except ValueError as exc:
        raise PreflightError(
            "PG14_HOST_PGDATA and PG18_HOST_PGDATA are incompatible paths"
        ) from exc
    if common in (source, target):
        raise PreflightError(
            "PG14_HOST_PGDATA and PG18_HOST_PGDATA must be sibling paths, not nested"
        )
    if not source.is_dir():
        raise PreflightError(f"PG14_HOST_PGDATA does not exist: {source}")
    source_marker = _marker(source, allow_nested=True)
    if source_marker != "14":
        raise PreflightError(
            f"PG14_HOST_PGDATA must contain PostgreSQL 14 PG_VERSION, got {source_marker!r}"
        )
    if not target.is_dir():
        raise PreflightError(f"validated PG18 target is unavailable: {target}")
    target_marker = _marker(target, allow_nested=False)
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
    args = parser.parse_args()
    try:
        source, target = validate_deployment_paths(args.source, args.target)
    except PreflightError as exc:
        print(f"[EE] {exc}")
        return 2
    print(f"PG14_HOST_PGDATA_CANON={source}")
    print(f"PG18_HOST_PGDATA_CANON={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
