.ONESHELL:

include .env

SERVICES:=
# options: dev, prod
ENV:=$(ENV)

DOCKER=docker-compose \
	--env-file .env \
	--project-name infodengue-$(ENV) \
	--file docker/compose-$(ENV).yaml

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

# DOCKER
.PHONY:docker-build
docker-build:
	$(DOCKER) build ${SERVICES}

.PHONY:docker-start-ci
docker-start-ci:
	$(DOCKER) up -d

.PHONY:docker-start
docker-start:
	$(DOCKER) up -d ${SERVICES}

.PHONY:docker-stop
docker-stop:
	$(DOCKER) stop ${SERVICES}

.PHONY:docker-exec
docker-exec:
	$(DOCKER) exec ${SERVICES} bash

.PHONY:docker-restart
docker-restart: docker-stop docker-start
	echo "[II] Docker services restarted!"

.PHONY:docker-logs
docker-logs:
	$(DOCKER) logs --follow --tail 100 ${SERVICES}

.PHONY:run-dev-db
docker-run-dev-db:
	$(DOCKER) run --rm db postgres -V

# Migrate databases and create shapefiles to synchronize with static_files
.PHONY:django-migrate
django-migrate: docker-run-dev-db
	$(DOCKER) run --rm web python3 manage.py migrate --database=dados --noinput
	$(DOCKER) run --rm web python3 manage.py migrate --database=infodengue --noinput
	$(DOCKER) run --rm web python3 manage.py migrate forecast --database=forecast

.PHONY:django-static-geofiles
django-static-geofiles:
	$(DOCKER) run --rm web python3 manage.py sync_geofiles
	$(DOCKER) run --rm web python3 manage.py collectstatic --noinput

.PHONY:test-staging-web
test-staging-web:
	$(DOCKER) run --no-deps web bash /opt/services/test.sh dados
	$(DOCKER) run --no-deps web bash /opt/services/test.sh dbf
	$(DOCKER) run --no-deps web bash /opt/services/test.sh gis
	$(DOCKER) run --no-deps web bash /opt/services/test.sh api
	#$(DOCKER) run --no-deps web bash /opt/services/test.sh forecast

.PHONY:test-staging-all
test-staging-all:
	$(DOCKER) run --rm web python3 manage.py test


.PHONY: lint
lint: ## formatting linter with poetry
	pre-commit install
	pre-commit run --all-files

# [CRON] Uses for web services
.PHONY:send-mail-partner
send-mail-partner:
	$(DOCKER) run --rm web python manage.py send_mail

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
