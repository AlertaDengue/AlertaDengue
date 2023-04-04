#!/bin/sh

## Usage:
##   . ./export-env.sh ; $COMMAND

unamestr=$(uname)
if [ "$unamestr" = 'Linux' ]; then

  export $(grep -v '^#' .env | xargs -d '\n')

elif [ "$unamestr" = 'FreeBSD' ] || [ "$unamestr" = 'Darwin' ]; then

  export $(grep -v '^#' .env | xargs -0)

fi

exec env subst <> /opt/services/AlertaDengue/.env
