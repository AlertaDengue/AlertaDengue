#!/usr/bin/env bash

# echo "Creating geofiles..."
# python3 manage.py sync_geofiles

echo "Collecting static files..."
python3 manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn -w 4 -b 0.0.0.0:8000 ad_main.wsgi:application --timeout 9640
