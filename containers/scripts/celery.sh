#!/usr/bin/env bash
set -euo pipefail

# Respect DJANGO_SETTINGS_MODULE from the container environment.
# If not set, default to dev.
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-ad_main.settings.dev}"

echo "[INFO] Starting celery..."
celery \
  --app=ad_main.celeryapp:app \
  worker -Ofair -l INFO -B
