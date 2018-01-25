from django.core.management.base import BaseCommand
# local

from datetime import datetime
# local
from ... import mapfile
from ...settings import RASTER_METEROLOGICAL_DATA_RANGE
from dados.dbdata import CID10


class Command(BaseCommand):
    help = 'Generate map files'

    def generate_mapfiles_alert(self):
        """

        :return:
        """
        for disease in CID10.keys():
            print('>> Generating %s mapfile' % disease)
            mf = mapfile.MapFileAlert(map_class=disease)
            mf.create_files()

    def generate_mapfiles_meteorological(self, date_start):
        """

        :return:
        """
        for c in RASTER_METEROLOGICAL_DATA_RANGE:
            print('>> Generating %s mapfile' % c)
            mf = mapfile.MapFileMeteorological(
                map_class=c, date_start=date_start
            )
            mf.create_files()

    def handle(self, *args, **options):
        _date_start = input(
            'Type the initial date of the the raster' +
            ' files to process (Y-m-d): '
        )
        date_start = datetime.strptime(_date_start, '%Y-%m-%d')
        print('Start date "%s" defined.' % date_start)

        print('\nGenerating mapfiles alert')
        self.generate_mapfiles_alert()
        print('\nGenerating mapfiles meteorological')
        self.generate_mapfiles_meteorological(date_start)
