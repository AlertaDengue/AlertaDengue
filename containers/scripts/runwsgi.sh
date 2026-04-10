#!/usr/bin/env bash

set -euo pipefail

if [[ "${ENV:-dev}" != "dev" ]]; then
  exec gunicorn ad_main.wsgi:application \
    --workers "${GUNICORN_WORKERS:-4}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --bind "0.0.0.0:${DJANGO_PORT:-8000}"
else
  exec python manage.py runserver "0.0.0.0:${DJANGO_PORT:-8000}"
fi
