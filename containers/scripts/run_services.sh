#!/usr/bin/env bash


set +ex

exec "$@" &
. /opt/services/celery.sh
