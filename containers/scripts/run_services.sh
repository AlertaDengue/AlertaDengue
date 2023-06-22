#!/usr/bin/env bash

# Disable printing of executed commands and enable error checking
set +ex

# Set the Django settings module to ad_main.settings
export DJANGO_SETTINGS_MODULE=ad_main.settings

# Execute the provided command in the background
exec "$@" &

# Source the celery.sh script
. /opt/services/celery.sh
