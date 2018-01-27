# Prepare MapServer

Define these settings variables (AlertaDengue/settings.ini):

* RASTER_PATH
* RASTER_METEROLOGICAL_DATA_RANGE
* SHAPEFILE_PATH
* MAPFILE_PATH
* MAPSERVER_LOG_PATH
* MAPSERVER_URL

The raster files are structures as bellow:

```txt
RASTER_PATH
  |- meteorological
  |    |- country
  |    |    |- lst_day_1km
  |    |    |- ...
  |    |- city
  |    |    |- lst_day_1km
  |    |    |   |- 12345678
  |    |    |   |- ...
  |    |    |- ...
```

```
Note 1: 12345678 was used as a geocode.
```

```
Note 2: The folder named with class image name (e.g. lst_day_1km),
should be written with lower case. Example:

* lst_day_1km
* lst_night_1km
* ndvi
* precipitation
* relative_humidity_2m_above_ground
* specific_humidity_2m_above_ground
```


## Generating meteorological geotiffs, alert and meteorological mapfiles

After these configuration is done, execute:

```sh

python manage.py generate_meteorological_raster_cities
```

```sh

python manage.py generate_mapfiles
```

The script will ask you a initial date to process the raster meteorological 
files.

Inside of each class image folder (e.g. lst_day_1km) there is one folder for 
each city, named with its geocode. For each city, the files is saved with the 
date as name (e.g. 20170101.tif)


## Using MapServer Docker

To build the MapServer Docker image, type (at the project root directory):

```sh
docker build -t alertadengue/mapserver --file Dockerfile-mapserver .
```

If you want to use docker-compose, you need to set the following variables:

* DOCKER_HOST_MAPFILES_DIR
* DOCKER_HOST_SHAPEFILES_DIR
* DOCKER_HOST_TIFFS_DIR
* DOCKER_HOST_LOG_DIR

You can create and run this MapServer instance using:

```sh
docker run -v /var/www/mapserver/mapfiles:/maps:ro \
    -v $(pwd)/AlertaDengue/static/shapefile:/shapefiles:ro \
    -v /var/www/mapserver/tiffs:/tiffs:ro \
    -v /var/www/mapserver/log/:/var/log/mapserver \
    -it --name mapserver alertadengue/mapserver
```

Before you run your container, create a error.log file on your mapserver/log folder with 777 permission mode.
