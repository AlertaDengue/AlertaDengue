compose_cmd = sudo docker-compose
staging_compose_cmd = sudo docker-compose -p infodengue_staging -f docker-compose.yml -f staging-compose.yml

build:
	$(compose_cmd) build
	$(compose_cmd) run --rm web python3 manage.py migrate --noinput
	$(compose_cmd) run --rm web python3 manage.py sync_geofiles
	$(compose_cmd) run --rm web python3 manage.py collectstatic --no-input

deploy: build
	$(compose_cmd) up -d


build_staging:
	$(staging_compose_cmd) build
	$(staging_compose_cmd) run --rm staging_db postgres -V
	$(staging_compose_cmd) run --rm web python3 manage.py migrate --noinput
	$(staging_compose_cmd) run --rm web python3 manage.py sync_geofiles
	$(staging_compose_cmd) run --rm web python3 manage.py collectstatic --no-input

deploy_staging: build_staging
	$(staging_compose_cmd) up -d

stop_staging:
	$(staging_compose_cmd) stop
