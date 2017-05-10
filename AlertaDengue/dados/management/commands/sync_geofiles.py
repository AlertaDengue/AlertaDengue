from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dados import maps, dbdata

import geojson
import os
import fiona


class Command(BaseCommand):
    help = 'Generates geojson files and save into staticfiles folder'

    def create_geojson(self, f_path, geo_id):
        """
        
        :param f_path: 
        :param geo_id: 
        :return: 
        """
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

    def create_shapefile(self, f_path, geo_id):
        """
        
        :param f_path: 
        :param geo_id: 
        :return: 
        """
        geojson_path = os.path.join(f_path, 'geojson', '%s.json' % geo_id)
        shpfile_path = os.path.join(f_path, 'shapefile', '%s.shp' % geo_id)

        # creates the shapefile
        with fiona.open(geojson_path) as geojson_file:
            with fiona.open(
                shpfile_path, "w",
                crs=geojson_file.crs,
                driver="ESRI Shapefile",
                schema=geojson_file.schema.copy()
            ) as shp:
                for item in geojson_file:
                    shp.write(item)

        self.stdout.write(
            self.style.SUCCESS(
                'Successfully shpfile %s synchronized!' % geo_id
            )
        )

    def handle(self, *args, **options):
        geo_ids = list(dict(dbdata.get_all_active_cities()).keys())

        _static_root = os.path.abspath(settings.STATIC_ROOT)
        _static_dirs = os.path.abspath(settings.STATICFILES_DIRS[0])

        path_root = (
            _static_root if os.path.exists(_static_root) else
            _static_dirs
        )

        f_geojson_path = os.path.join(path_root, 'geojson')
        f_shapefile_path = os.path.join(path_root, 'shapefile')

        if not os.path.exists(f_geojson_path):
            os.mkdir(f_geojson_path, mode=0o777)

        if not os.path.exists(f_shapefile_path):
            os.mkdir(f_shapefile_path, mode=0o777)

        for geo_id in geo_ids:
            self.create_geojson(f_geojson_path, geo_id)
            self.create_shapefile(path_root, geo_id)

        print('Done.')