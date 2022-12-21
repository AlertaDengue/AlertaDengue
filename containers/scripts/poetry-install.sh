#!/usr/bin/env bash

set -ex

if [[ $ENV == "prod" ]]; then
  export POETRY_INSTALL_ARGS="--no-dev"
fi

poetry config virtualenvs.create false
poetry install $POETRY_INSTALL_ARGS
