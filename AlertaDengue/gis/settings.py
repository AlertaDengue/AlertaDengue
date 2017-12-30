try:
    # to be used externally (such as notebooks science)
    from AlertaDengue.AlertaDengue import settings
except:
    from django.conf import settings

BASE_DIR = settings.BASE_DIR
RASTER_PATH = settings.RASTER_PATH
RASTER_METEROLOGICAL_DATA_RANGE = settings.RASTER_METEROLOGICAL_DATA_RANGE