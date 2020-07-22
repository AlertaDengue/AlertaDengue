# Deploy production and staging
# note: --env-file requires docker-compose>=1.25
#       ref: https://github.com/docker/compose/pull/6535

include $(ENVFILE)
export

compose_cmd = docker-compose -p infodengue -f docker/docker-compose.yml --env-file .env
staging_compose_cmd = docker-compose -f docker/staging-compose.yml --env-file .env_staging


SERVICES_STAGING :=


build:
	$(compose_cmd) build

build_migrate: build
	$(compose_cmd) run --rm web python3 manage.py migrate --noinput
	$(compose_cmd) run --rm web python3 manage.py migrate --database=forecast --noinput

deploy: build_migrate
	$(compose_cmd) up -d

generate_maps: build_migrate
	$(compose_cmd) run --rm web python3 manage.py sync_geofiles
	$(compose_cmd) run --rm web python3 manage.py generate_meteorological_raster_cities
	$(compose_cmd) run --rm web python3 manage.py generate_mapfiles
	$(compose_cmd) run --rm web python3 manage.py python3 manage.py collectstatic --noinput

stop:
	$(compose_cmd) stop


build_staging:
	$(staging_compose_cmd) build ${SERVICES_STAGING}


build_migrate_staging: build_staging
	$(staging_compose_cmd) run --rm staging_db postgres -V
	$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate --noinput
	#$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate --database=forecast --noinput
	$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate --database=infodengue --noinput

deploy_staging: build_migrate_staging
	$(staging_compose_cmd) up -d


start_staging_db_demo:
	$(staging_compose_cmd) up -d staging_db_demo

start_staging_db:
	$(staging_compose_cmd) up -d staging_db

# Exemplo: make start_staging SERVICES=staging_db
start_staging:
	$(staging_compose_cmd) up -d ${SERVICES_STAGING}

stop_staging:
	$(staging_compose_cmd) stop

generate_maps_staging: build_migrate_staging
	$(staging_compose_cmd) run --rm staging_web python3 manage.py sync_geofiles
	# $(staging_compose_cmd) run --rm staging_web python3 manage.py generate_meteorological_raster_cities
	# $(staging_compose_cmd) run --rm staging_web python3 manage.py generate_mapfiles
	$(staging_compose_cmd) run --rm staging_web python3 manage.py collectstatic --noinput

clean_staging:
	$(staging_compose_cmd) stop
	$(staging_compose_cmd) rm

# Clean containers and images docker
build_remove_orphans:
	$(compose_cmd) up --build --remove-orphans

build_remove_orphans_staging:
	$(staging_compose_cmd) up staging_web --remove-orphans

remove_stoped_containers:
	docker rm $(docker ps -a -q)

remove_untagged_images:
	docker rmi $(docker images | grep "^<none>" | awk "{print $3}")


# Docker TEST

flake8_staging: build_staging
	$(staging_compose_cmd) run --rm --no-deps staging_web flake8

test_staging_web: generate_maps_staging
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh dados
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh dbf
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh gis
	$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh api
	#$(staging_compose_cmd) run --no-deps staging_web bash ../docker/test.sh forecast

install:
	pip install -e .
