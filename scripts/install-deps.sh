#!/usr/bin/env bash
set -ex

# cd to repo root
SCRIPT_PATH="${BASH_SOURCE:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

if [[ "$ENV" == "prod" ]]; then
  ${SCRIPT_DIR}/install-prod.sh
else
  ${SCRIPT_DIR}/install-dev.sh
fi
set +ex
