from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FULL_BACKUP_LABEL_RE = re.compile(r"^[0-9]{8}-[0-9]{6}F$")
FORBIDDEN_PGDATA_PATHS = {
    "/",
    "/var",
    "/opt",
    "/srv",
    "/Storage",
    "/home",
}
APPROVED_PGDATA_ROOTS_BY_PROFILE = {
    "dev": (
        Path("/opt/data/infodengue/dev"),
        Path("/srv/workspace/infodengue/dev"),
    ),
    "staging": (
        Path("/opt/data/infodengue/staging"),
        Path("/opt/data/staging"),
        Path("/srv/workspace/infodengue/staging"),
    ),
    "prod": (
        Path("/opt/data/infodengue/prod"),
        Path("/srv/workspace/infodengue/prod"),
    ),
}


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class RefreshInputs:
    source_repo: Path
    host_pgdata: Path
    backup_set: str


@dataclass(frozen=True)
class ProfileRestoreInputs:
    profile: str
    host_pgdata: Path
    backup_set: str


def require_confirmation(confirm: str, *, expected: str) -> None:
    if confirm != expected:
        raise ValidationError(
            f"Refusing operation without --confirm {expected}."
        )


def validate_full_backup_label(label: str) -> str:
    if not FULL_BACKUP_LABEL_RE.fullmatch(label):
        raise ValidationError(
            "Backup label must be an explicit full backup label matching "
            "YYYYMMDD-HHMMSSF."
        )
    return label


def _require_non_empty_path(raw_path: str, label: str) -> str:
    if not raw_path or not raw_path.strip():
        raise ValidationError(f"{label} must not be empty.")
    return raw_path


def _canonicalize(raw_path: str) -> Path:
    return Path(os.path.realpath(raw_path))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _validate_profile(profile: str) -> str:
    if profile not in APPROVED_PGDATA_ROOTS_BY_PROFILE:
        raise ValidationError(f"Invalid profile: {profile!r}")
    return profile


def _approved_roots_for_profile(profile: str) -> tuple[Path, ...]:
    validated_profile = _validate_profile(profile)
    return APPROVED_PGDATA_ROOTS_BY_PROFILE[validated_profile]


def validate_source_repo(source_repo: str) -> Path:
    raw_path = _require_non_empty_path(source_repo, "--source-repo")
    if not os.path.isabs(raw_path):
        raise ValidationError("--source-repo must be an absolute path.")

    repo_path = Path(raw_path)
    if not repo_path.is_dir():
        raise ValidationError(f"Source repository does not exist: {raw_path}")

    canonical = _canonicalize(raw_path)
    required_paths = (
        canonical / "backup" / "prod" / "backup.info",
        canonical / "archive" / "prod" / "archive.info",
    )
    for required_path in required_paths:
        if not required_path.is_file():
            raise ValidationError(
                f"Required source path is missing: {required_path}"
            )

    return canonical


def validate_host_pgdata(
    host_pgdata: str,
    *,
    approved_roots: tuple[Path, ...],
    source_repo: Path | None = None,
) -> Path:
    raw_path = _require_non_empty_path(host_pgdata, "HOST_PGDATA")
    if not os.path.isabs(raw_path):
        raise ValidationError(f"HOST_PGDATA must be an absolute path: {raw_path}")

    pgdata_path = Path(raw_path)
    if pgdata_path.is_symlink():
        raise ValidationError(f"HOST_PGDATA must not be a symbolic link: {raw_path}")

    canonical = _canonicalize(raw_path)
    canonical_text = os.fspath(canonical)
    if canonical_text in FORBIDDEN_PGDATA_PATHS:
        raise ValidationError(
            f"HOST_PGDATA points to a forbidden path: {canonical_text}"
        )

    approved_root = None
    for root in approved_roots:
        if _is_relative_to(canonical, root):
            approved_root = root
            break
        if canonical == root:
            raise ValidationError(
                "HOST_PGDATA must include at least one path component below "
                f"the approved root: {root}"
            )

    if approved_root is None:
        approved = ", ".join(os.fspath(root) + "/" for root in approved_roots)
        raise ValidationError(
            "HOST_PGDATA must be under an approved profile root: "
            f"{approved}"
        )

    if source_repo is not None:
        if canonical == source_repo:
            raise ValidationError("HOST_PGDATA must not equal the source repository.")
        if _is_relative_to(canonical, source_repo):
            raise ValidationError("HOST_PGDATA must not be contained by the source repository.")
        if _is_relative_to(source_repo, canonical):
            raise ValidationError("HOST_PGDATA must not contain the source repository.")

    return canonical


def validate_refresh_inputs(
    *,
    source_repo: str,
    host_pgdata: str,
    backup_set: str,
    confirm: str,
) -> RefreshInputs:
    require_confirmation(confirm, expected="REFRESH-STAGING-FROM-PROD")
    validated_backup_set = validate_full_backup_label(backup_set)
    validated_source_repo = validate_source_repo(source_repo)
    validated_host_pgdata = validate_host_pgdata(
        host_pgdata,
        approved_roots=_approved_roots_for_profile("staging"),
        source_repo=validated_source_repo,
    )
    return RefreshInputs(
        source_repo=validated_source_repo,
        host_pgdata=validated_host_pgdata,
        backup_set=validated_backup_set,
    )


def validate_profile_restore_inputs(
    *, profile: str, host_pgdata: str, backup_set: str, confirm: str
) -> ProfileRestoreInputs:
    validated_profile = _validate_profile(profile)
    require_confirmation(confirm, expected="RESTORE-PROFILE-BACKUP")
    validated_backup_set = validate_full_backup_label(backup_set)
    validated_host_pgdata = validate_host_pgdata(
        host_pgdata,
        approved_roots=_approved_roots_for_profile(validated_profile),
    )
    return ProfileRestoreInputs(
        profile=validated_profile,
        host_pgdata=validated_host_pgdata,
        backup_set=validated_backup_set,
    )


def _load_json(stdin_text: str) -> Any:
    try:
        return json.loads(stdin_text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON input: {exc}") from exc


def _coerce_stanza_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("stanza", "stanzas", "info"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    raise ValidationError("pgBackRest info output must be a JSON object or array.")


def _status_is_valid(status: Any) -> bool:
    if not isinstance(status, dict):
        return False
    code = status.get("code")
    message = str(status.get("message", "")).strip().lower()
    if code == 0:
        return True
    return message == "ok"


def _extract_db_version(backup: dict[str, Any], stanza: dict[str, Any]) -> Any:
    database = backup.get("database")
    if isinstance(database, dict) and "version" in database:
        return database["version"]

    db_entries = stanza.get("db")
    if isinstance(db_entries, list) and db_entries:
        first = db_entries[0]
        if isinstance(first, dict) and "version" in first:
            return first["version"]

    return None


def _is_postgresql_14(version: Any) -> bool:
    if version is None:
        return False
    version_text = str(version).strip()
    if version_text == "14":
        return True
    if version_text.startswith("14."):
        return True
    if version_text.isdigit() and 140000 <= int(version_text) < 150000:
        return True
    return False


def _extract_backup_size(backup: dict[str, Any]) -> int | None:
    candidates = []

    info = backup.get("info")
    if isinstance(info, dict):
        candidates.extend(
            (
                info.get("size"),
                info.get("backup-size"),
                info.get("database", {}).get("size")
                if isinstance(info.get("database"), dict)
                else None,
            )
        )

    database = backup.get("database")
    if isinstance(database, dict):
        candidates.extend((database.get("size"), database.get("backup-size")))

    for candidate in candidates:
        if candidate is None:
            continue
        try:
            size = int(candidate)
        except (TypeError, ValueError):
            continue
        if size > 0:
            return size

    return None


def select_backup_from_info(
    payload: Any, *, stanza_name: str, backup_label: str
) -> int:
    stanzas = _coerce_stanza_list(payload)
    stanza = next(
        (
            entry
            for entry in stanzas
            if entry.get("name") == stanza_name or entry.get("stanza") == stanza_name
        ),
        None,
    )
    if stanza is None:
        raise ValidationError(f"Required stanza was not found: {stanza_name}")

    repo_entries = stanza.get("repo")
    if not isinstance(repo_entries, list) or not repo_entries:
        raise ValidationError("pgBackRest info did not report repository status.")
    if not all(_status_is_valid(entry.get("status")) for entry in repo_entries):
        raise ValidationError("pgBackRest repository status is not valid.")

    backups = stanza.get("backup")
    if not isinstance(backups, list):
        raise ValidationError("pgBackRest info did not include backup metadata.")

    selected_backup = next(
        (
            entry
            for entry in backups
            if isinstance(entry, dict) and entry.get("label") == backup_label
        ),
        None,
    )
    if selected_backup is None:
        raise ValidationError(f"Requested backup label was not found: {backup_label}")

    backup_type = selected_backup.get("type")
    if backup_type != "full":
        raise ValidationError(
            f"Requested backup must be full, got: {backup_type!r}"
        )

    version = _extract_db_version(selected_backup, stanza)
    if not _is_postgresql_14(version):
        raise ValidationError(
            f"Requested backup must target PostgreSQL 14, got: {version!r}"
        )

    db_size = _extract_backup_size(selected_backup)
    if db_size is None:
        raise ValidationError(
            "Requested backup is missing a positive database backup size."
        )

    return db_size


def validate_volume_labels(labels: dict[str, Any]) -> None:
    expected_labels = {
        "com.docker.compose.project": "infodengue-staging",
        "com.docker.compose.volume": "pgbackrest_repo",
    }
    for key, expected_value in expected_labels.items():
        actual_value = labels.get(key)
        if actual_value != expected_value:
            raise ValidationError(
                f"Docker volume label {key!r} must equal {expected_value!r}, "
                f"got {actual_value!r}."
            )


def validate_restored_database(
    *,
    source_db_size: int,
    data_directory: str,
    in_recovery: str,
    relation_exists: str,
    db_size: int,
) -> None:
    if in_recovery != "f":
        raise ValidationError("PostgreSQL is still in recovery.")
    if data_directory != "/var/lib/postgresql/data":
        raise ValidationError(f"Unexpected data_directory: {data_directory}")
    if relation_exists != "t":
        raise ValidationError(
            'Expected relation "Dengue_global"."Municipio" was not found.'
        )
    if db_size <= 0:
        raise ValidationError("Restored database size must be greater than zero.")
    if db_size * 10 < source_db_size * 9:
        raise ValidationError(
            "Restored database is smaller than 90% of the source backup size."
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate pgBackRest staging refresh inputs and metadata."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_inputs_parser = subparsers.add_parser("validate-inputs")
    validate_inputs_parser.add_argument("--source-repo", required=True)
    validate_inputs_parser.add_argument("--host-pgdata", required=True)
    validate_inputs_parser.add_argument("--backup-set", required=True)
    validate_inputs_parser.add_argument("--confirm", required=True)

    validate_profile_restore_parser = subparsers.add_parser(
        "validate-profile-restore-inputs"
    )
    validate_profile_restore_parser.add_argument("--profile", required=True)
    validate_profile_restore_parser.add_argument("--host-pgdata", required=True)
    validate_profile_restore_parser.add_argument("--backup-set", required=True)
    validate_profile_restore_parser.add_argument("--confirm", required=True)

    validate_info_parser = subparsers.add_parser("validate-pgbackrest-info")
    validate_info_parser.add_argument("--stanza", required=True)
    validate_info_parser.add_argument("--backup-set", required=True)

    subparsers.add_parser("validate-volume-labels")

    validate_restore_parser = subparsers.add_parser("validate-restore")
    validate_restore_parser.add_argument("--source-db-size", type=int, required=True)
    validate_restore_parser.add_argument("--data-directory", required=True)
    validate_restore_parser.add_argument("--in-recovery", required=True)
    validate_restore_parser.add_argument("--relation-exists", required=True)
    validate_restore_parser.add_argument("--db-size", type=int, required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "validate-inputs":
            result = validate_refresh_inputs(
                source_repo=args.source_repo,
                host_pgdata=args.host_pgdata,
                backup_set=args.backup_set,
                confirm=args.confirm,
            )
            print(f"SOURCE_REPO_CANON={result.source_repo}")
            print(f"HOST_PGDATA_CANON={result.host_pgdata}")
            print(f"BACKUP_SET={result.backup_set}")
            return 0

        if args.command == "validate-profile-restore-inputs":
            result = validate_profile_restore_inputs(
                profile=args.profile,
                host_pgdata=args.host_pgdata,
                backup_set=args.backup_set,
                confirm=args.confirm,
            )
            print(f"PROFILE={result.profile}")
            print(f"HOST_PGDATA_CANON={result.host_pgdata}")
            print(f"BACKUP_SET={result.backup_set}")
            return 0

        if args.command == "validate-pgbackrest-info":
            payload = _load_json(sys.stdin.read())
            db_size = select_backup_from_info(
                payload,
                stanza_name=args.stanza,
                backup_label=args.backup_set,
            )
            print(f"SOURCE_BACKUP_DB_SIZE={db_size}")
            return 0

        if args.command == "validate-volume-labels":
            payload = _load_json(sys.stdin.read())
            if not isinstance(payload, dict):
                raise ValidationError("Docker volume labels must be a JSON object.")
            validate_volume_labels(payload)
            return 0

        if args.command == "validate-restore":
            validate_restored_database(
                source_db_size=args.source_db_size,
                data_directory=args.data_directory,
                in_recovery=args.in_recovery,
                relation_exists=args.relation_exists,
                db_size=args.db_size,
            )
            return 0
    except ValidationError as exc:
        print(f"[EE] {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
