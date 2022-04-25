SERVICES:=
# options: dev, prod
ENV:=dev

DOCKER=docker-compose \
	--env-file .env \
	--project-name infodengue-$(ENV) \
	--file docker/compose-$(ENV).yaml



# PREPARE ENVIRONMENT
.PHONY:prepare-env
prepare-env:
	# source env_export.sh
	# python generate_paths.py
	envsubst < .env.tpl > .env


# DOCKER
.PHONY:docker-build
docker-build:
	$(DOCKER) build ${SERVICES}

.PHONY:docker-start
docker-start:
	$(DOCKER) up -d ${SERVICES}

.PHONY:docker-stop
docker-stop:
	$(DOCKER) stop ${SERVICES}

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
.PHONY:docker-restart
django-migrate: django-migrate
	$(DOCKER) run --rm web python3 manage.py migrate --database=dados --noinput
	$(DOCKER) run --rm web python3 manage.py migrate --database=infodengue --noinput
	$(DOCKER) run --rm web python3 manage.py migrate forecast --database=forecast

.PHONY:django-static-geofiles
django-static-geofiles:
	$(DOCKER) run --rm web python3 manage.py sync_geofiles
	$(DOCKER) run --rm web python3 manage.py collectstatic --noinput

.PHONY:docker-restart
test-infodengue-web:
	$(DOCKER) run --no-deps web bash ../docker/test.sh dados
	$(DOCKER) run --no-deps web bash ../docker/test.sh dbf
	$(DOCKER) run --no-deps web bash ../docker/test.sh gis
	$(DOCKER) run --no-deps web bash ../docker/test.sh api
	#$(DOCKER) run --no-deps web bash ../docker/test.sh forecast

.PHONY:test-infodengue-all
test-infodengue-all: #deploy_staging
	$(DOCKER) run --rm web python3 manage.py test

# [CRON] Uses for web services
.PHONY:send-mail-partner
send-mail-partner:
	$(compose_cmd) run --rm web python manage.py send_mail

.PHONY:clean
clean:
	@find ./ -name '*.pyc' -exec rm -f {} \;
	@find ./ -name '*.pyo' -exec rm -f {} \;
	@find ./ -name '*~' -exec rm -f {} \;
	rm -rf .cache
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
