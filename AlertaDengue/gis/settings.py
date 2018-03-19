try:
    # to be used externally (such as notebooks science)
    from AlertaDengue.AlertaDengue import settings
except:
    from django.conf import settings

BASE_DIR = settings.BASE_DIR
RASTER_PATH = settings.RASTER_PATH
RASTER_METEROLOGICAL_DATA_RANGE = settings.RASTER_METEROLOGICAL_DATA_RANGE

SHAPEFILE_PATH = settings.SHAPEFILE_PATH
MAPFILE_PATH = settings.MAPFILE_PATH
MAPSERVER_LOG_PATH = settings.MAPSERVER_LOG_PATH
MAPSERVER_URL = settings.MAPSERVER_URL
RASTER_METEROLOGICAL_FACTOR_INCREASE = (
    settings.RASTER_METEROLOGICAL_FACTOR_INCREASE
)
DEBUG = settings.DEBUG
