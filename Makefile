.ONESHELL:

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

CONSOLE:=bash

# PREPARE ENVIRONMENT
.PHONY:prepare-env
prepare-env:
	# SHELL := /usr/bin/sh
	# source ../scripts/env_variables_export.sh
	# python ../scripts/create_env_directories.py
	envsubst < env.tpl > .env

# PREPARE CREATE GEOFILES FOR STATIC
.PHONY:sync-static-geofiles
sync-static-geofiles:
	python AlertaDengue/manage.py sync_geofiles
	python AlertaDengue/manage.py collectstatic --noinput

# CONTAINER_APP

.PHONY:container-build
container-build:
	$(CONTAINER_APP) build base
	$(CONTAINER_APP) build ${SERVICES}

.PHONY:container-start
container-start:
	$(CONTAINER_APP) up -d ${SERVICES}

.PHONY:container-stop
container-stop:
	$(CONTAINER_APP) stop ${SERVICES}

.PHONY:container-exec
container-exec:
	$(CONTAINER_APP) exec ${SERVICES} bash

.PHONY:container-restart
container-restart: container-stop container-start
	echo "[II] Docker services restarted!"

#* Test containers build on Ci
.PHONY: container-run-all
container-run-all: ## build and deploy all containers
	$(CONTAINER_APP) up -d --build

.PHONY:container-logs
container-logs:
	$(CONTAINER_APP) logs --tail 300 ${SERVICES}

.PHONY:container-logs-follow
container-logs-follow:
	$(CONTAINER_APP) logs --follow --tail 300 ${SERVICES}

.PHONY: container-wait
container-wait:
	ENV=${ENV} timeout 90 ./containers/scripts/healthcheck.sh ${SERVICE}

.PHONY: container-wait-all
container-wait-all:
	$(MAKE) container-wait ENV=${ENV} SERVICE="memcached"
	$(MAKE) container-wait ENV=${ENV} SERVICE="rabbitmq"
	if [[ ${ENV} -eq "dev"]]; then $(MAKE) container-wait ENV=${ENV} SERVICE="db"; fi
	$(MAKE) container-wait ENV=${ENV} SERVICE="web"
	$(MAKE) container-wait ENV=${ENV} SERVICE="worker"

.PHONY:container-console
container-console:
	$(CONTAINER_APP) exec ${SERVICE} ${CONSOLE}

.PHONY:container-down
container-down:
	$(CONTAINER_APP) down --volumes

.PHONY:run-dev-db
container-run-dev-db:
	$(CONTAINER_APP) run --rm db postgres -V

# Migrate databases and create shapefiles to synchronize with static_files
.PHONY:django-migrate
django-migrate: container-run-dev-db
	$(CONTAINER_APP) run --rm web python3 manage.py migrate --database=dados --noinput
	$(CONTAINER_APP) run --rm web python3 manage.py migrate --database=infodengue --noinput
	$(CONTAINER_APP) run --rm web python3 manage.py migrate forecast --database=forecast

.PHONY:django-static-geofiles
django-static-geofiles:
	$(CONTAINER_APP) run --rm web python3 manage.py sync_geofiles
	$(CONTAINER_APP) run --rm web python3 manage.py collectstatic --noinput

.PHONY:test-staging-web
test-staging-web:
	$(CONTAINER_APP) run --no-deps web bash /opt/services/test.sh dados
	$(CONTAINER_APP) run --no-deps web bash /opt/services/test.sh dbf
	$(CONTAINER_APP) run --no-deps web bash /opt/services/test.sh gis
	$(CONTAINER_APP) run --no-deps web bash /opt/services/test.sh api
	#$(CONTAINER_APP) run --no-deps web bash /opt/services/test.sh forecast

.PHONY:test-staging-all
test-staging-all:
	$(CONTAINER_APP) run --rm web python3 manage.py test


.PHONY: lint
lint: ## formatting linter with poetry
	pre-commit install
	pre-commit run --all-files

# [CRON] Uses for web services
.PHONY:send-mail-partner
send-mail-partner:
	$(CONTAINER_APP) run --rm web python manage.py send_mail

# Python
.PHONY: clean
clean: ## clean all artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr .idea/
	rm -fr */.eggs
	rm -fr db
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '*.ipynb_checkpoints' -exec rm -rf {} +
	find . -name '*.pytest_cache' -exec rm -rf {} +
