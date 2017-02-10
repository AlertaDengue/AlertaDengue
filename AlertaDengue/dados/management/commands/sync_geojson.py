from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dados import maps, dbdata

import geojson
import os


class Command(BaseCommand):
    help = 'Generates geojson files and save into staticfiles folder'

    def handle(self, *args, **options):
        geo_ids = list(dict(dbdata.get_all_active_cities()).keys())

        _static_root = os.path.abspath(settings.STATIC_ROOT)
        _static_dirs = os.path.abspath(settings.STATICFILES_DIRS[0])

        path_root = (
            _static_root if os.path.exists(_static_root) else
            _static_dirs
        )

        f_path = os.path.join(path_root, 'geojson')

        if not os.path.exists(f_path):
            os.mkdir(f_path, mode=0o777)

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
