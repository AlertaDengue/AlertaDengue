import os
from datetime import datetime

from ad_main.settings import DEBUG, RASTER_METEROLOGICAL_DATA_RANGE
from django.core.management.base import BaseCommand

# local
from gis import geotiff

# local


class Command(BaseCommand):
    help = "Generate map files"

    def generate_meteorological_cities_raster(self, date_start):
        """

        :return:
        """
        for c in RASTER_METEROLOGICAL_DATA_RANGE:
            if DEBUG:
                log_path = os.path.join(os.sep, "tmp", "raster_%s.log" % c)
                with open(log_path, "w") as f:
                    f.write("")

            print(">> Generating %s raster files" % c)
            geotiff.MeteorologicalRaster.generate_raster_cities(
                raster_class=c, date_start=date_start
            )

    def handle(self, *args, **options):
        str_date_start = (
            None  # TODO: receive str_date_start from command line #343
        )
        if str_date_start:
            date_start = datetime.strptime(str_date_start, "%Y-%m-%d")
            print('Start date "%s" defined.' % date_start)
        else:
            date_start = None

        print("\nGenerating meteorological cities raster")
        self.generate_meteorological_cities_raster(date_start)
