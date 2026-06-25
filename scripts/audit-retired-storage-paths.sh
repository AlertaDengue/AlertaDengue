#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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

SYSTEM_SEARCH_DIRS=(
  "/etc/systemd/system"
  "/etc/cron.d"
  "/etc/cron.daily"
  "/etc/cron.hourly"
  "/etc/cron.monthly"
  "/etc/cron.weekly"
  "/usr/local/bin"
)

print_header() {
  printf "\n== %s ==\n" "$1"
}

check_path() {
  local path="$1"

  if [[ -e "$path" ]]; then
    printf "present  %s\n" "$path"
    du -sh "$path" 2>/dev/null || true
  else
    printf "missing   %s\n" "$path"
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
