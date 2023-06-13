#!/usr/bin/env bash


set +ex

echo "[INFO] Starting collectstatics..."
python3 manage.py collectstatic --noinput

exec "$@" &
. /opt/services/celery.sh
