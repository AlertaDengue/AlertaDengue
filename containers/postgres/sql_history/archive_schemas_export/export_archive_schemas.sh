#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${ARCHIVE_WORKFLOW_INTERNAL:-0}" != "1" ]]; then
  printf 'Direct execution is not supported. Use archive_schemas_workflow.sh export.\n' >&2
  exit 1
fi

[[ $# -eq 1 ]] || {
  printf 'internal usage: %s <resolved-output-root>\n' "${0##*/}" >&2
  exit 1
}

exec "${SCRIPT_DIR}/archive_schemas_workflow.sh" _export-internal "$1"
