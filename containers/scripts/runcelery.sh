#!/usr/bin/env bash
set -euo pipefail

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-ad_main.settings.dev}"

celery_concurrency="${CELERY_WORKER_CONCURRENCY:-4}"
celery_pool="${CELERY_WORKER_POOL:-prefork}"
celery_loglevel="${CELERY_LOGLEVEL:-INFO}"

extra_opts=()
if [[ -n "${CELERY_WORKER_OPTS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_opts=(${CELERY_WORKER_OPTS})
fi

echo "[INFO] Starting celery worker (pool=${celery_pool}, " \
     "concurrency=${celery_concurrency})..."

exec celery \
  --app=ad_main.celeryapp:app \
  worker \
  -Ofair \
  --loglevel "${celery_loglevel}" \
  --pool "${celery_pool}" \
  --concurrency "${celery_concurrency}" \
  "${extra_opts[@]}"
