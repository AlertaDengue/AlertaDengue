#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-ad_main.settings.testing}"

if [[ "$#" -gt 0 ]]; then
  exec poetry run mypy "$@"
fi

exec poetry run mypy   AlertaDengue/ad_main   AlertaDengue/api   AlertaDengue/dados   AlertaDengue/ingestion   AlertaDengue/manager
