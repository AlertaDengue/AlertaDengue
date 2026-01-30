#!/usr/bin/env bash
set -euo pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-ad_main.settings.dev}"

celery_loglevel="${CELERY_LOGLEVEL:-INFO}"
schedule_file="${CELERYBEAT_SCHEDULE:-/tmp/celerybeat-schedule}"

extra_opts=()
if [[ -n "${CELERY_BEAT_OPTS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_opts=(${CELERY_BEAT_OPTS})
fi

echo "[INFO] Starting celery beat (schedule=${schedule_file})..."

exec celery \
  --app=ad_main.celeryapp:app \
  beat \
  --loglevel "${celery_loglevel}" \
  --schedule "${schedule_file}" \
  "${extra_opts[@]}"
