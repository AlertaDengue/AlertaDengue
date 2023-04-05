#!/bin/sh

## Usage:
##   . ./export-env.sh ; $COMMAND

unamestr=$(uname)
if [ "$unamestr" = 'Linux' ]; then

  export $(grep -v '^#' .env | xargs -d '\n')

fi

exec envsubst < .env_episcanner.tpl > /opt/services/AlertaDengue/.env
