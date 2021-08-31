# Deploy production and staging
# note: --env-file requires docker-compose>=1.25
#       ref: https://github.com/docker/compose/pull/6535

include .env_staging .env
export

compose_cmd = docker-compose -p infodengue -f docker/docker-compose.yml --env-file .env
staging_compose_cmd = docker-compose -p info -f docker/staging-compose.yml --env-file .env_staging
SERVICES_INFODENGUE :=
SERVICES_STAGING :=
MAKE = make -f Makefile

# Create the containers to run in production
build:
	$(compose_cmd) build ${SERVICES_INFODENGUE}

migrate:
	$(compose_cmd) run --rm web python3 manage.py migrate --noinput
	$(compose_cmd) run --rm web python3 manage.py migrate dbf --database=infodengue --noinput
	# $(compose_cmd) run --rm web python3 manage.py migrate forecast --database=forecast --noinput

deploy: migrate
	$(compose_cmd) up -d ${SERVICES_INFODENGUE}

generate_maps: build_migrate
	$(compose_cmd) run --rm web python3 manage.py sync_geofiles
	$(compose_cmd) run --rm web python3 manage.py generate_meteorological_raster_cities
	$(compose_cmd) run --rm web python3 manage.py generate_mapfiles
	$(compose_cmd) run --rm web python3 manage.py collectstatic --noinput

exec:
	$(compose_cmd) exec ${SERVICES_INFODENGUE} bash

stop:
	$(compose_cmd) stop ${SERVICES_INFODENGUE}

# Exemplo: make start_staging SERVICES=staging_web
start_staging:
	$(staging_compose_cmd) up -d ${SERVICES_STAGING}

# Used for make deploy
up_staging_db:
	$(staging_compose_cmd) up -d staging_db

exec_staging:
	$(staging_compose_cmd) exec ${SERVICES_STAGING} bash

stop_staging:
	$(staging_compose_cmd) stop ${SERVICES_STAGING}

build_staging:
	$(staging_compose_cmd) build ${SERVICES_STAGING}

deploy_staging: up_staging_db
	$(MAKE) migrate_staging
	$(staging_compose_cmd) up -d

run_staging_db:
	$(staging_compose_cmd) run --rm staging_db postgres -V

## Migrate databases and create shapefiles to synchronize with static_files
migrate_staging: run_staging_db
	$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate --database=dados --noinput
	$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate --database=infodengue --noinput
	$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate forecast --database=forecast

generate_maps_staging:
	$(staging_compose_cmd) run --rm staging_web python3 manage.py sync_geofiles
	$(staging_compose_cmd) run --rm staging_web python3 manage.py collectstatic --noinput
	$(staging_compose_cmd) run --rm staging_web python3 manage.py generate_meteorological_raster_cities
	$(staging_compose_cmd) run --rm staging_web python3 manage.py generate_mapfiles

## Tests for containers in the CI
flake8_staging:
	$(staging_compose_cmd) run --rm --no-deps staging_web flake8

test_staging_web:
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh dados
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh dbf
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh gis
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh api
	#$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh forecast

test_all: #deploy_staging
	$(staging_compose_cmd) run --rm staging_web python3 manage.py test


# Clean containers and images docker
remove_stoped_containers:
	docker rm $(docker ps -a -q)

remove_untagged_images:
	docker rmi $(docker images | grep "^<none>" | awk "{print $3}")


# Uses for development
develop:
	pip install --user -e .

install:
	pip install .

sync_mapfiles:
	python AlertaDengue/manage.py sync_geofiles
	python AlertaDengue/manage.py generate_meteorological_raster_cities
	python AlertaDengue/manage.py generate_mapfiles
	python AlertaDengue/manage.py collectstatic --noinput

run_alertadengue:
	python AlertaDengue/manage.py runserver

# Uses for cron
send_mail_partner:
	$(compose_cmd) run --rm web python manage.py send_mail

clean:
	@find ./ -name '*.pyc' -exec rm -f {} \;
	@find ./ -name '*.pyo' -exec rm -f {} \;
	@find ./ -name '*~' -exec rm -f {} \;
	rm -rf .cache
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
