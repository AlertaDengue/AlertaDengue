#!/bin/bash
DEPLOY_HOME="/opt/services/"
NUM_WORKERS=4
WSGI_HOST="0.0.0.0"
WSGI_PORT="8000"
ERRLOG="$DEPLOY_HOME/logs/wsgi_server.err"
ACCESS_LOG="$DEPLOY_HOME/logs/wsgi_server.access"

echo "Collecting static files.."
python3 manage.py collectstatic --noinput
# echo "Creating geofiles..."
# python3 manage.py sync_geofiles

exec gunicorn -w $NUM_WORKERS -b $WSGI_HOST:$WSGI_PORT ad_main.wsgi:application --timeout 9640
