from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dados import maps, dbdata

import geojson
import os


class Command(BaseCommand):
    help = 'Generates geojson files and save into staticfiles folder'

    def handle(self, *args, **options):
        geo_ids = list(dict(dbdata.get_all_active_cities()).keys())

        for geo_id in geo_ids:
            f_name = os.path.join(
                settings.STATICFILES_DIRS[0], 'geojson', '%s.json' % geo_id
            )

            geojson_city = geojson.dumps(
                maps.get_city_geojson(int(geo_id))
            )
            with open(f_name, 'w') as f:
                f.write(geojson_city)

            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully geojson %s synchronized!' % geo_id
                )
            )
