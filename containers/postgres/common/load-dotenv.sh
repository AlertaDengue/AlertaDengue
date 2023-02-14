#!/usr/bin/env bash

path="$(readlink -f "${BASH_SOURCE:-$0}")"
DIR_PATH="$(dirname $path)"

source "${DIR_PATH}/get-project-path.sh"

export $(echo $(cat ${PROJECT_PATH}/.env_prod | sed 's/#.*//g'| xargs) | envsubst)
