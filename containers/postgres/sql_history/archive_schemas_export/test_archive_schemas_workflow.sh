#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW="${SCRIPT_DIR}/archive_schemas_workflow.sh"
RESTORE="${SCRIPT_DIR}/restore_archive_schemas_validation.sh"

bash -n "$WORKFLOW" "$RESTORE"
for schema in archive_redemet archive_upload archive_ovitrampa archive_alertas_regionais archive_cemaden archive_copernicus archive_historico_casos archive_mosqlimate archive_tweets archive_dbf_upload archive_sinan_upload; do
  grep -q "$schema" "$WORKFLOW" "$RESTORE"
done
grep -q 'selected_schemas.tsv' "$WORKFLOW" "$RESTORE"
grep -q 'createdb -T template0' "$RESTORE"
grep -q 'disposable_removal' "$RESTORE"

if [[ -z "${PGDATABASE:-}" || -z "${PGUSER:-}" ]]; then
  printf 'archive schema static tests: PASS (live tests require external libpq configuration)\n'
  exit 0
fi

expect_fail() {
  local label="$1"
  shift
  if "$@" >/tmp/archive_schema_test.out 2>/tmp/archive_schema_test.err; then
    printf 'expected failure did not occur: %s\n' "$label" >&2
    exit 1
  fi
}

"$WORKFLOW" status --schemas archive_dbf_upload,archive_sinan_upload >/tmp/archive_schema_status.out
expect_fail public "$WORKFLOW" status --schemas public
expect_fail not_allowlisted "$WORKFLOW" status --schemas archive_not_allowed
expect_fail duplicate "$WORKFLOW" status --schemas archive_dbf_upload,archive_dbf_upload
expect_fail empty "$WORKFLOW" status --schemas ''
expect_fail metacharacter "$WORKFLOW" status --schemas 'archive_dbf_upload;DROP'
expect_fail old_missing "$WORKFLOW" status --schemas archive_tweets
printf 'archive schema workflow tests: PASS\n'
