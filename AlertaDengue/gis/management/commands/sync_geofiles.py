from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
# local
from dados import maps, dbdata
from ...geodf import extract_boundaries

import geojson
import geopandas as gpd
import json
import numpy as np
import os
import fiona


class Command(BaseCommand):
    help = 'Generates geojson files and save into staticfiles folder'

    def create_geojson(self, f_path, geocode):
        """
        
        :param f_path: 
        :param geocode: 
        :return: 
        """
        f_name = os.path.join(f_path, '%s.json' % geocode)

        geojson_city = geojson.dumps(
            maps.get_city_geojson(int(geocode))
        )

        with open(f_name, 'w') as f:
            f.write(geojson_city)

        self.stdout.write(
            self.style.SUCCESS(
                'Successfully geojson %s synchronized!' % geocode
            )
        )

    def create_shapefile(self, f_path, geocode):
        """
        
        :param f_path: 
        :param geocode: 
        :return: 
        """
        geojson_path = os.path.join(f_path, 'geojson', '%s.json' % geocode)
        shpfile_path = os.path.join(f_path, 'shapefile', '%s.shp' % geocode)

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
                'Successfully shpfile %s synchronized!' % geocode
            )
        )

    def extract_geo_info_table(self, f_path, geocode):
        """

        :param f_path:
        :param geocode:
        :return:
        """
        shpfile_path = os.path.join(f_path, 'shapefile', '%s.shp' % geocode)
        
        gdf = gpd.read_file(shpfile_path)
        
        bounds = extract_boundaries(gdf).tolist()
        width = abs(bounds[0] - bounds[2])
        height = abs(bounds[1] - bounds[3])

        return {
            geocode: {
                'bounds': bounds,
                'width': width,
                'height': height
            }
        }

    def handle(self, *args, **options):
        geocodes = list(dict(dbdata.get_all_active_cities()).keys())

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

        geo_info = {}

        for geocode in geocodes:
            self.create_geojson(f_geojson_path, geocode)
            self.create_shapefile(path_root, geocode)
            geo_info.update(self.extract_geo_info_table(
                path_root, geocode
            ))

        with open(os.path.join(f_geojson_path, 'geo_info.json'), 'w') as f:
            json.dump(geo_info, f)
            print('[II] Geo Info JSON saved!')

        print('[II] DONE!')
