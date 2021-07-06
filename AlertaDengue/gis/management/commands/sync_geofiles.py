import json
import os

import fiona
import geojson
import geopandas as gpd
import shapely

# local
from dados import dbdata, maps
from django.conf import settings
from django.core.management.base import BaseCommand
from shapely.geometry import MultiPolygon, shape

from ...geodf import extract_boundaries


class Command(BaseCommand):
    help = 'Generates geojson files and save into staticfiles folder'

    def create_geojson(self, f_path, geocode):
        """
        :param f_path:
        :param geocode:
        :return:
        """
        f_name = os.path.join(f_path, '%s.json' % geocode)

        geojson_city = geojson.dumps(maps.get_city_geojson(int(geocode)))

        with open(f_name, 'w') as f:
            f.write(geojson_city)

        self.stdout.write(
            self.style.SUCCESS(
                'Successfully geojson %s synchronized!' % geocode
            )
        )

    def get_geojson(self, f_path, geocode):
        f_name = os.path.join(f_path, '%s.json' % geocode)

        with open(f_name, 'r') as f:
            return json.load(f)

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
                shpfile_path,
                "w",
                crs=geojson_file.crs,
                driver="ESRI Shapefile",
                schema=geojson_file.schema.copy(),
            ) as shp:
                for item in geojson_file:
                    shp.write(item)

    def simplify_geojson(self, f_path, geocode):
        """
        :param f_path:
        :param geocode:
        :return:
        """
        geojson_simplified_path = os.path.join(
            f_path, 'geojson_simplified', '%s.json' % geocode
        )
        geojson_original_path = os.path.join(
            f_path, 'geojson', '%s.json' % geocode
        )

        geojson_simplified_dir_path = os.path.dirname(geojson_simplified_path)
        os.makedirs(geojson_simplified_dir_path, mode=0o777, exist_ok=True)

        if not os.path.exists(geojson_original_path):
            self.stdout.write(
                self.style.WARNING(
                    'GeoJSON/simplified %s not synchronized!' % geocode
                )
            )
            return

        # creates the shapefile
        with fiona.open(geojson_original_path, 'r') as shp:
            polygon_list = [shape(pol['geometry']) for pol in shp]

            if len(polygon_list) == 1 and isinstance(
                polygon_list[0], MultiPolygon
            ):
                multipolygon = polygon_list[0]
            else:
                multipolygon = MultiPolygon(polygon_list)

            shp_min = multipolygon.simplify(0.005)
            with open(geojson_simplified_path, 'w') as f:
                geojson_geometry = shapely.geometry.mapping(shp_min)
                geojson_content = {
                    'type': 'Feature',
                    'id': str(geocode),
                    'properties': shp[0]['properties'],
                    'geometry': geojson_geometry,
                }
                json.dump(geojson_content, f)

        self.stdout.write(
            self.style.SUCCESS(
                'Successfully GeoJSON/simplified %s synchronized!' % geocode
            )
        )

    def create_geojson_by_state(self, geojson_simplified_path):
        # create jsonfiles by state
        # note: uses 2 steps to minimize memory consumption

        # create a dictionary with geocode by ufs
        geojson_codes_states = {
            state_code: [] for state_code in dbdata.ALL_STATE_NAMES.keys()
        }
        for (
            geocode,
            _,
            _,
            state_name,
        ) in dbdata.get_all_active_cities_state():
            state_code = dbdata.STATE_INITIAL[state_name]
            geojson_codes_states[state_code].append(geocode)

        geojson_states: dict = {
            state_code: {'type': 'FeatureCollection', 'features': []}
            for state_code in dbdata.ALL_STATE_NAMES.keys()
        }

        for state_code, geocodes in geojson_codes_states.items():
            for geocode in geocodes:
                geojson_content = self.get_geojson(
                    geojson_simplified_path, geocode
                )
                # add id attribute
                geojson_states[state_code]['features'].append(geojson_content)

        for state_code, geojson_state in geojson_states.items():
            f_name = os.path.join(
                geojson_simplified_path, '{}.json'.format(state_code)
            )
            with open(f_name, 'w') as f:
                json.dump(geojson_state, f)

            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully GeoJson/simplified %s.json stored!'
                    % state_code
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

        return {geocode: {'bounds': bounds, 'width': width, 'height': height}}

    def handle(self, *args, **options):
        geocodes = list(dict(dbdata.get_all_active_cities()).keys())

        _static_root = os.path.abspath(settings.STATIC_ROOT)
        _static_dirs = os.path.abspath(settings.STATICFILES_DIRS[0])

        path_root = (
            _static_root if os.path.exists(_static_root) else _static_dirs
        )

        f_geojson_path = os.path.join(path_root, 'geojson')
        f_geojson_simplified_path = os.path.join(
            path_root, 'geojson_simplified'
        )
        f_shapefile_path = os.path.join(path_root, 'shapefile')

        if not os.path.exists(f_geojson_path):
            os.makedirs(f_geojson_path, mode=0o777)

        if not os.path.exists(f_shapefile_path):
            os.makedirs(f_shapefile_path, mode=0o777)

        geo_info = {}

        for geocode in geocodes:
            self.create_geojson(f_geojson_path, geocode)
            self.create_shapefile(path_root, geocode)
            self.simplify_geojson(path_root, geocode)
            geo_info.update(self.extract_geo_info_table(path_root, geocode))

        self.create_geojson_by_state(f_geojson_simplified_path)

        with open(os.path.join(f_geojson_path, 'geo_info.json'), 'w') as f:
            json.dump(geo_info, f)
            print('[II] Geo Info JSON saved!')

        print('[II] DONE!')
