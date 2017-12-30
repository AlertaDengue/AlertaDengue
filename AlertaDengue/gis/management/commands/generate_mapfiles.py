from django.core.management.base import BaseCommand
from gis.mapfile import generate_alert_mapfiles


class Command(BaseCommand):
    help = 'Generate map files'

    def handle(self, *args, **options):
        generate_alert_mapfiles()
        print('DONE')
