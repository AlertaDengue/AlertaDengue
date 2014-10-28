#!/bin/bash

source /srv/deploy/project/bin/activate
# For some reason supervisord is not passing $HOME to this script, and because
# of that we get errors like trying to use "//.python-eggs" as $PYTHON_EGG_CACHE
export HOME="/srv/deploy"
exec $*
