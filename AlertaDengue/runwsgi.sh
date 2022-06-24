#!/bin/bash

set -a
source .env
set +a
exec $@

NUM_WORKERS=4
WSGI_HOST="0.0.0.0"

if [[ ${DEBUG} = 'True' ]]; then
    ENV='Development'
    WSGI_PORT="8080"
else
    ENV='Production'
    WSGI_PORT="8000"
fi

echo "I - Collecting static files.."
python3 manage.py collectstatic --noinput

echo "II - Start gunicorn in ${ENV} mode...."
exec gunicorn -w $NUM_WORKERS -b $WSGI_HOST:$WSGI_PORT ad_main.wsgi:application --timeout 9640
