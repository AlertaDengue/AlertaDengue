from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dados import maps, dbdata

import geojson
import os


class Command(BaseCommand):
    help = 'Generates geojson files and save into staticfiles folder'

    def handle(self, *args, **options):
        geo_ids = list(dict(dbdata.get_all_active_cities()).keys())

        if not os.path.exists(settings.STATIC_ROOT):
            os.makedirs(settings.STATIC_ROOT)

        f_path = os.path.join(
            os.path.abspath(settings.STATIC_ROOT),
            'geojson'
        )

        if not os.path.exists(f_path):
            os.makedirs(f_path)

        for geo_id in geo_ids:
            f_name = os.path.join(f_path, '%s.json' % geo_id)

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
