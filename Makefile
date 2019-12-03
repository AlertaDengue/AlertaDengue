# Deploy production and staging
compose_cmd = docker-compose -p infodengue -f docker-compose.yml
staging_compose_cmd = docker-compose -p infodengue_staging -f staging-compose.yml

# Build and remove containers --orphans
build_remove = docker-compose -p infodengue up --build --remove-orphans
build_remove_staging = docker-compose -p infodengue_staging up staging_web --remove-orphans

#Remove all stopped containers and ntagged images
remove_stoped_containers = docker rm $(docker ps -a -q)
remove_untagged_images = docker rmi $(docker images | grep "^<none>" | awk "{print $3}")


build:
	$(compose_cmd) build
	$(compose_cmd) run --rm web python3 manage.py migrate --noinput
	$(compose_cmd) run --rm web python3 manage.py migrate --database=forecast --noinput

deploy: build
	$(compose_cmd) up -d

generate_maps: build
	$(compose_cmd) run --rm web python3 manage.py sync_geofiles
	$(compose_cmd) run --rm web python3 manage.py generate_meteorological_raster_cities
	$(compose_cmd) run --rm web python3 manage.py generate_mapfiles

stop:
	$(compose_cmd) stop


build_staging:
	$(staging_compose_cmd) build
	$(staging_compose_cmd) run --rm staging_db postgres -V
	$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate --noinput
	$(staging_compose_cmd) run --rm staging_web python3 manage.py migrate --database=forecast --noinput

deploy_staging: build_staging
	$(staging_compose_cmd) up -d

stop_staging:
	$(staging_compose_cmd) stop

generate_maps_staging: build
	$(staging_compose_cmd) run --rm web python3 manage.py sync_geofiles
	$(staging_compose_cmd) run --rm web python3 manage.py generate_meteorological_raster_cities
	$(staging_compose_cmd) run --rm web python3 manage.py generate_mapfiles

clean_staging:
	$(staging_compose_cmd) stop
	$(staging_compose_cmd) rm


#Clean containers and images docker
remove_orphans:
	$(build_remove)

remove_orphans_staging:
	$(build_remove_staging )

remove_stoped_containers:
	$(remove_stoped_containers)

remove_untagged_images:
	$(remove_untagged_images)