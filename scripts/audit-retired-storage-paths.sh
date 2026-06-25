#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SYSTEM_SEARCH_DIRS=(
  "/etc/systemd/system"
  "/etc/cron.d"
  "/etc/cron.daily"
  "/etc/cron.hourly"
  "/etc/cron.monthly"
  "/etc/cron.weekly"
  "/usr/local/bin"
)

PROFILE=""
declare -a RETIRED_DIRS=()
declare -a PROTECTED_DIRS=()

usage() {
  cat <<'EOF'
Usage:
  bash scripts/audit-retired-storage-paths.sh --profile staging
  bash scripts/audit-retired-storage-paths.sh --profile prod \
    --retired-path /old/path \
    --protected-path /active/path

Options:
  --profile <name>         Profile inventory to load. Supported: staging, prod.
  --retired-path <path>    Add a retired path to audit. Repeatable.
  --protected-path <path>  Add a protected path to audit. Repeatable.
  --help                   Show this help.

Notes:
  - The script never removes paths. It only audits and prints suggested commands.
  - Production retired paths must be passed explicitly to avoid guessing.
EOF
}

append_unique() {
  local value="$1"
  shift
  local -n target="$1"
  local item

  for item in "${target[@]:-}"; do
    if [[ "$item" == "$value" ]]; then
      return 0
    fi
  done

  target+=("$value")
}

load_profile_defaults() {
  case "$PROFILE" in
    staging)
      RETIRED_DIRS=(
        "/opt/data/staging/sftp2/alertadengue"
        "/opt/data/staging/sftp2/alertadengue/dbfs_parquet"
        "/opt/data/staging/img/incidence_maps"
        "/opt/services/staging_AlertaDengue/staticfiles"
        "/opt/data/staging/sftp2/alertadengue/uploaded"
      )
      PROTECTED_DIRS=(
        "/mnt/storagebox-staging/sinan"
        "/mnt/storagebox-staging/sinan/imported"
        "/opt/data/staging/sinan/incoming/"
        "/opt/data/staging/shapefiles"
        "/opt/data/staging/tiffs"
        "/opt/data/staging/episcanner"
      )
      ;;
    prod)
      PROTECTED_DIRS=(
        "/mnt/storagebox-infodengue/sinan"
        "/mnt/storagebox-infodengue/sinan/imported"
      )
      ;;
    *)
      printf "Unsupported profile: %s\n" "$PROFILE" >&2
      exit 1
      ;;
  esac
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile)
        PROFILE="${2:-}"
        shift 2
        ;;
      --retired-path)
        append_unique "${2:-}" RETIRED_DIRS
        shift 2
        ;;
      --protected-path)
        append_unique "${2:-}" PROTECTED_DIRS
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        printf "Unknown argument: %s\n" "$1" >&2
        usage >&2
        exit 1
        ;;
    esac
  done
}

print_header() {
  printf "\n== %s ==\n" "$1"
}

check_path() {
  local path="$1"

  if [[ -e "$path" ]]; then
    printf "present  %s\n" "$path"
    du -sh "$path" 2>/dev/null || true
  else
    printf "missing  %s\n" "$path"
  fi
}

search_references() {
  local path="$1"
  local found=1

  printf "repo refs for %s\n" "$path"
  if rg -n -F "$path" "$ROOT_DIR" \
    --glob '!node_modules/**' \
    --glob '!.git/**' \
    --glob '!docs/unused-volume-path-cleanup-plan.md' \
    --glob '!scripts/audit-retired-storage-paths.sh'; then
    found=0
  else
    printf "none in repo\n"
  fi

  printf "system refs for %s\n" "$path"
  if rg -n -F "$path" "${SYSTEM_SEARCH_DIRS[@]}" 2>/dev/null; then
    found=0
  else
    printf "none in scanned system paths\n"
  fi

  return "$found"
}

validate_inputs() {
  if [[ -z "$PROFILE" ]]; then
    printf "Missing required argument: --profile\n" >&2
    usage >&2
    exit 1
  fi

  load_profile_defaults

  if [[ ${#RETIRED_DIRS[@]} -eq 0 ]]; then
    printf "No retired paths configured for profile '%s'.\n" "$PROFILE" >&2
    printf "Pass them explicitly with --retired-path.\n" >&2
    exit 1
  fi

  if [[ ${#PROTECTED_DIRS[@]} -eq 0 ]]; then
    printf "No protected paths configured for profile '%s'.\n" "$PROFILE" >&2
    printf "Pass them explicitly with --protected-path.\n" >&2
    exit 1
  fi
}

main() {
  parse_args "$@"
  validate_inputs

  print_header "Profile"
  printf "%s\n" "$PROFILE"

  print_header "Retired Path Inventory"
  for path in "${RETIRED_DIRS[@]}"; do
    check_path "$path"
  done

  print_header "Protected Paths"
  for path in "${PROTECTED_DIRS[@]}"; do
    check_path "$path"
  done

  print_header "Reference Scan"
  for path in "${RETIRED_DIRS[@]}"; do
    search_references "$path" || true
    printf "\n"
  done

  print_header "Suggested Manual Removal Commands"
  for path in "${RETIRED_DIRS[@]}"; do
    printf "sudo rm -rf %q\n" "$path"
  done
}

main "$@"
