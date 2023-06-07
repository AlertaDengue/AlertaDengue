#!/usr/bin/env bash


set +ex

python3 manage.py collectstatic --noinput

exec gunicorn -w 4 -b 0.0.0.0:8000 ad_main.wsgi:application --timeout 9640 &

. /opt/services/celery.sh
