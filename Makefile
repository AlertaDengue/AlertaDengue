compose_cmd = sudo docker-compose

build:
	$(compose_cmd) build
	$(compose_cmd) run --rm web python3 manage.py migrate --noinput
	$(compose_cmd) run --rm web python3 manage.py sync_geofiles
	$(compose_cmd) run --rm web python3 manage.py collectstatic --no-input

deploy: build
	$(compose_cmd) up -d
