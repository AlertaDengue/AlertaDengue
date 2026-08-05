#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW="${SCRIPT_DIR}/archive_schemas_workflow.sh"
RESTORE="${SCRIPT_DIR}/restore_archive_schemas_validation.sh"

bash -n "$WORKFLOW" "$RESTORE"
grep -q "archive_dbf_upload" "$WORKFLOW"
grep -q "archive_sinan_upload" "$WORKFLOW"
! grep -Eq 'archive_(redemet|upload|ovitrampa|alertas_regionais|cemaden|copernicus|historico_casos|mosqlimate|tweets)' "$WORKFLOW" "$RESTORE"
grep -q 'createdb -T template0' "$RESTORE"
grep -q 'disposable_removal' "$RESTORE"
printf 'archive schema workflow static tests: PASS\n'
