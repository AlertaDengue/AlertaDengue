from django.core.management.base import BaseCommand
# local

from datetime import datetime
# local
from ... import mapfile
from ...settings import RASTER_METEROLOGICAL_DATA_RANGE
from dados.dbdata import CID10

import os


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
        str_date_start = input(
            'Type the initial date of the the raster' +
            ' files to process (Y-m-d): '
        )

        if str_date_start:
            date_start = datetime.strptime(str_date_start, '%Y-%m-%d')
            print('Start date "%s" defined.' % date_start)
        else:
            date_start = None

        print('\nGenerating mapfiles alert')
        self.generate_mapfiles_alert()
        print('\nGenerating mapfiles meteorological')
        self.generate_mapfiles_meteorological(date_start)
