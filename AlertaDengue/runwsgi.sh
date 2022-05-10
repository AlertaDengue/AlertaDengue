#!/bin/bash
NUM_WORKERS=4
WSGI_HOST="0.0.0.0"
WSGI_PORT="8000"
ERRLOG="/opt/services/logs/wsgi_server.err"
ACCESS_LOG="/opt/services/logs/wsgi_server.access"

echo "Creating geofiles..."
python3 manage.py sync_geofiles

echo "Collecting static files.."
python3 manage.py collectstatic --noinput

exec gunicorn -w $NUM_WORKERS -b $WSGI_HOST:$WSGI_PORT ad_main.wsgi:application --timeout 9640
