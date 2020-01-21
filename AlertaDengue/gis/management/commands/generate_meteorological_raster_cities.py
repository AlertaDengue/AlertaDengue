from django.core.management.base import BaseCommand
# local

from datetime import datetime
# local
from ... import geotiff
from ...settings import RASTER_METEROLOGICAL_DATA_RANGE, DEBUG

import os


class Command(BaseCommand):
    help = 'Generate map files'

    def generate_meteorological_cities_raster(self, date_start):
        """

        :return:
        """
        for c in RASTER_METEROLOGICAL_DATA_RANGE:
            if DEBUG:
                log_path = os.path.join(os.sep, 'tmp', 'raster_%s.log' % c)
                with open(log_path, 'w') as f:
                    f.write('')

            print('>> Generating %s raster files' % c)
            geotiff.MeteorologicalRaster.generate_raster_cities(
                raster_class=c, date_start=date_start
            )

    def handle(self, *args, **options):
        str_date_start = input(
            'Type the initial date of the the raster' +
            ' files to process (Y-m-d): '
        )

        if str_date_start:
            date_start = datetime.strptime(str_date_start, '%Y-%m-%d')
            print('Start date "%s" defined.' % date_start)
        else:
            date_start = None

        print('\nGenerating meteorological cities raster')
        self.generate_meteorological_cities_raster(date_start)
