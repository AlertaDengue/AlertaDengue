#* Variables
SHELL:=/usr/bin/env bash
ARGS:=
CONSOLE:=bash
TIMEOUT:=180

include .env

SERVICES:=
SERVICE:=
# options: dev, prod
ENV:=$(ENV)

CONTAINER_APP=docker-compose \
	--env-file .env \
	--project-name infodengue-$(ENV) \
	--file containers/compose-base.yaml \
	--file containers/compose-$(ENV).yaml

# PREPARE ENVIRONMENT
.PHONY:prepare-env
prepare-env:
	# SHELL := /usr/bin/sh
	# source ../scripts/env_variables_export.sh
	# python ../scripts/create_env_directories.py
	envsubst < .env.tpl > .env

# 
.PHONY: container-wait
container-wait:
	ENV=${ENV} timeout ${TIMEOUT} ./containers/scripts/healthcheck.sh ${SERVICE}

.PHONY: container-wait-all
container-wait-all:
	$(MAKE) container-wait ENV=${ENV} SERVICE="memcached"
	$(MAKE) container-wait ENV=${ENV} SERVICE="rabbitmq"
	if [[ "${ENV}" == "dev" ]]; then make container-wait ENV=dev SERVICE="postgres"; fi
	$(MAKE) container-wait ENV=${ENV} SERVICE="web"

# 
.PHONY:test-staging-all
test-staging-all:
	$(CONTAINER_APP) run --rm web python3 manage.py test
