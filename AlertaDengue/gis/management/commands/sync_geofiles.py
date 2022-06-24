import json
import os
from pathlib import Path

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
    help = "Generates geojson files and save into staticfiles folder"

    def create_geojson(self, f_path, geocode):
        """
        :param f_path:
        :param geocode:
        :return:
        """

        f_name = f_path / f"{geocode}.json"

        geojson_city = geojson.dumps(maps.get_city_geojson(int(geocode)))

        with open(f_name, "w") as f:
            f.write(geojson_city)

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully geojson %s synchronized!" % geocode
            )
        )

    def get_geojson(self, f_path, geocode):

        f_name = f_path / f"{geocode}.json"

        with open(f_name, "r") as f:
            return json.load(f)

    def create_shapefile(self, f_path, geocode):
        """
        :param f_path:
        :param geocode:
        :return:
        """

        geojson_path = f_path / "geojson" / f"{geocode}.json"
        shpfile_path = f_path / "shapefile" / f"{geocode}.shp"

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

        geojson_simplified_path = Path(
            f_path / "geojson_simplified" / f"{geocode}.json"
        )

        geojson_original_path = Path(f_path / "geojson" / f"{geocode}.json")

        geojson_simplified_dir_path = geojson_simplified_path.parent

        geojson_simplified_dir_path.mkdir(parents=True, exist_ok=True)

        if not geojson_original_path.exists():
            self.stdout.write(
                self.style.WARNING(
                    "GeoJSON/simplified %s not synchronized!" % geocode
                )
            )
            return

        # creates the shapefile
        with fiona.open(geojson_original_path, "r") as shp:
            polygon_list = [shape(pol["geometry"]) for pol in shp]

            if len(polygon_list) == 1 and isinstance(
                polygon_list[0], MultiPolygon
            ):
                multipolygon = polygon_list[0]
            else:
                multipolygon = MultiPolygon(polygon_list)

            shp_min = multipolygon.simplify(0.005)
            with open(geojson_simplified_path, "w") as f:
                geojson_geometry = shapely.geometry.mapping(shp_min)
                geojson_content = {
                    "type": "Feature",
                    "id": str(geocode),
                    "properties": shp[0]["properties"],
                    "geometry": geojson_geometry,
                }
                json.dump(geojson_content, f)

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully GeoJSON/simplified %s synchronized!" % geocode
            )
        )

    def create_geojson_by_state(self, geojson_simplified_path):
        # create jsonfiles by state
        # note: uses 2 steps to minimize memory consumption

        # create a dictionary with geocode by ufs
        geojson_codes_states = {
            state_code: [] for state_code in dbdata.STATE_NAME.keys()
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
            state_code: {"type": "FeatureCollection", "features": []}
            for state_code in dbdata.STATE_NAME.keys()
        }

        for state_code, geocodes in geojson_codes_states.items():
            for geocode in geocodes:
                geojson_content = self.get_geojson(
                    geojson_simplified_path, geocode
                )
                # add id attribute
                geojson_states[state_code]["features"].append(geojson_content)

        for state_code, geojson_state in geojson_states.items():
            f_name = geojson_simplified_path / f"{state_code}.json"

            with open(f_name, "w") as f:
                json.dump(geojson_state, f)

            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully GeoJson/simplified %s.json stored!"
                    % state_code
                )
            )

    def extract_geo_info_table(self, f_path, geocode):
        """
        :param f_path:
        :param geocode:
        :return:
        """

        shpfile_path = f_path / "shapefile" / f"{geocode}.shp"

        gdf = gpd.read_file(shpfile_path)

        bounds = extract_boundaries(gdf).tolist()
        width = abs(bounds[0] - bounds[2])
        height = abs(bounds[1] - bounds[3])

        return {geocode: {"bounds": bounds, "width": width, "height": height}}

    def handle(self, *args, **options):
        geocodes = list(dict(dbdata.get_all_active_cities()).keys())

        SERVE_STATIC = (
            settings.STATICFILES_DIRS[0]
            if settings.DEBUG
            else settings.STATIC_ROOT
        )

        path_root = Path(SERVE_STATIC)

        f_geojson_path = path_root / "geojson"

        f_geojson_simplified_path = path_root / "geojson_simplified"

        f_shapefile_path = path_root / "shapefile"

        f_geojson_path.mkdir(parents=True, exist_ok=True)

        f_shapefile_path.mkdir(parents=True, exist_ok=True)

        geo_info = {}

        for geocode in geocodes:
            self.create_geojson(f_geojson_path, geocode)
            self.create_shapefile(path_root, geocode)
            self.simplify_geojson(path_root, geocode)
            geo_info.update(self.extract_geo_info_table(path_root, geocode))

        # f_geojson_simplified_path.mkdir(parents=True, exist_ok=True)
        self.create_geojson_by_state(f_geojson_simplified_path)

        with open(os.path.join(f_geojson_path, "geo_info.json"), "w") as f:
            json.dump(geo_info, f)
            print("[II] Geo Info JSON saved!")

        print("[II] DONE!")
