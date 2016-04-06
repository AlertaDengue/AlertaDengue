#!/bin/bash
DEPLOY_HOME="/srv/deploy"
NUM_WORKERS=4
WSGI_HOST="127.0.0.1"
WSGI_PORT="8000"
ERRLOG="$DEPLOY_HOME/logs/wsgi_server.err"
ACCESS_LOG="$DEPLOY_HOME/logs/wsgi_server.access"

source "$DEPLOY_HOME/project/bin/activate"

# Supervisord is not passing $HOME to this script, and because of that we get
# errors like trying to use "//.python-eggs" as PYTHON_EGG_CACHE
export HOME=$DEPLOY_HOME
exec gunicorn -w $NUM_WORKERS -b $WSGI_HOST:$WSGI_PORT --error-logfile=$ERRLOG --access-logfile=$ACCESS_LOG AlertaDengue.wsgi:application --timeout 240
