from django.conf import settings
# local
from dados import dbdata
from dados.dbdata import STATE_INITIAL, CID10, db_engine
from .geodf import extract_boundaries

import geopandas as gpd
import numpy as np
import os
import pyproj


def stringfy_boundaries(bounds: np.array, sep=' '):
    str_boundaries = [str(v) for v in bounds]
    return sep.join(str_boundaries)


def calc_layer_width_by_boundaries(bounds: np.array, layer_height: int=400):
    # ratio size
    width = np.abs(bounds[0] - bounds[2])
    height = np.abs(bounds[1] - bounds[3])

    ratio_size = width / height

    return layer_height * ratio_size


def get_template_content(file_name: str):
    """

    :param file_name:
    :return:
    """
    current_dir = os.path.dirname(__file__)
    mapfile_template_dir = os.path.join(current_dir, 'templates', 'mapfile')

    with open(
        os.path.join(mapfile_template_dir, file_name)
    ) as f:
        return f.read()


def transform_boundaries(bounds: np.array, proj_from, proj_to):
    # boundaries in epsg:4326
    bounds[0], bounds[1] = pyproj.transform(
        proj_from, proj_to,
        bounds[0], bounds[1]
    )
    bounds[2], bounds[3] = pyproj.transform(
        proj_from, proj_to,
        bounds[2], bounds[3]
    )

    return bounds


class MapFile:
    path = {
        'shapefile_dir': settings.SHAPEFILE_PATH,
        'local_mapfile_dir': settings.MAPFILE_PATH,
        'mapserver_error': settings.MAPSERVER_LOG_PATH,
        'mapserver_cgi': settings.MAPSERVER_URL + '?map=%s&',
        'mapserver_shapefile_dir': '/shapefiles',
        'mapserver_mapfile_dir': '/maps/%s',
    }

    mapfile_name = '%s.map'

    # Getting general info geo from Brazil
    gdf_country = gpd.GeoDataFrame.from_file(
        os.path.join(path['shapefile_dir'], '%s.shp' % 'UFEBRASIL')
    )

    # http://all-geo.org/volcan01010/2012/11/change-coordinates-with-pyproj/
    # LatLon with WGS84 datum used by GPS units and Google Earth
    projections = {
        'wgs84': pyproj.Proj("+init=EPSG:4326"),
        'grs80': pyproj.Proj("+init=EPSG:2154")
    }

    # boundaries in epsg:2154
    bounds = transform_boundaries(
        bounds=extract_boundaries(gdf_country),
        proj_from=projections['grs80'],
        proj_to=projections['wgs84']
    )

    extent_country = stringfy_boundaries(bounds=bounds, sep=' ')

    crs_proj_country = 'epsg:2154'
    wms_srs_country = crs_proj_country.upper()

    map_template = ''
    layer_template = ''

    layer_height = 400
    layers = {}

    def create_files(self):
        self.create_layers()
        self.create_map()

    def create_layers(self):
        pass

    def create_map(self):
        pass

    def generate(self, template: str, parameters: dict, output_file_path: str):
        """

        :param template:
        :param parameters:
        :param output_file_path:
        :return:
        """
        with open(output_file_path, 'w') as f:
            f.write(template % parameters)


class MapFileAlert(MapFile):
    map_template = get_template_content('map.map')
    layer_template = get_template_content('layer_alert.map')
    alert_colors = [
        '#00FF00',
        '#FFFF00',
        '#FF9900',
        '#FF0000',
    ]
    diseases = tuple(CID10.keys())
    state_initials = STATE_INITIAL
    state_bounds = {}
    include_layers = {}

    template_url = (
        settings.MAPSERVER_URL + '?' +
        'map=/maps/dengue.map&' +
        'SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&' +
        'STYLES=&CRS=%(crs_url)s&BBOX=%(bbox)s&' +
        'WIDTH=%(width)s&HEIGHT=%(height)s&FORMAT=%%(format)s&' +
        'LAYERS=%(layer_name)s'
    )

    def create_layers(self):
        """

        :return:
        """
        include_template = (
            '  INCLUDE "layers/%(disease)s/%(layer_name)s"  # %(city_name)s\n'
        )

        sql_template = '''
        SELECT geocodigo, nome, uf 
        FROM "Dengue_global"."Municipio" 
        WHERE uf = '%s'
        ORDER BY nome;
        '''

        for disease in self.diseases:
            self.layers[disease] = {}
            self.state_bounds[disease] = {}
            self.include_layers[disease] = {}

            # layers by state
            for state_name in self.state_initials.keys():
                with db_engine.connect() as conn:
                    sql = sql_template % state_name
                    result = conn.execute(sql).fetchall()

                cities_alert = dbdata.NotificationResume.get_cities_alert_by_state(
                    state_name, disease
                )

                alerts = dict(
                    cities_alert[['municipio_geocodigo', 'level_alert']].values
                )

                self.layers[disease][state_name] = []
                self.include_layers[disease][state_name] = ''

                for geocode, city_name, state_country in result:
                    # getting shapefile settings
                    shapefile_path = os.path.join(self.shp_path, '%s.shp' % geocode)

                    if not os.path.exists(shapefile_path):
                        continue

                    gdf = gpd.GeoDataFrame.from_file(shapefile_path)

                    crs_proj = gdf.crs['init']
                    wms_srs = crs_proj.upper()
                    bounds = extract_boundaries(gdf)

                    layer_bbox = stringfy_boundaries(bounds=bounds, sep=',')
                    layer_width = calc_layer_width_by_boundaries(
                        bounds=bounds, layer_height=self.layer_height
                    )

                    alert_level = alerts[geocode] if geocode in alerts else -1
                    # print(alert_level)
                    alert_color = (
                        self.alert_colors[alert_level] if 0 <= alert_level <= 3 else
                        '#DFDFDF'  # gray
                    )

                    layer_name = city_name.upper().replace(' ', '_')

                    layer_conf = {
                        'geocode': geocode,
                        'city_name': city_name,
                        'layer_name': layer_name,
                        'rgb': alert_color,
                        'wms_srs': wms_srs,
                        'crs_proj': crs_proj,
                        'crs_url': (
                            crs_proj
                            if not crs_proj.upper() == 'EPSG:4326' else
                            'CRS:84'
                        ),
                        'bbox': layer_bbox,
                        'width': layer_width,
                        'height': self.layer_height
                    }

                    self.layers[disease][state_name] += [layer_conf]

                    layer_path_disease = self.local_mapfile_dir % (
                        'layers/%s/%%s' % disease
                    )

                    if not os.path.exists(layer_path_disease):
                        os.makedirs(layer_path_disease)

                    # layer_content = self.layer_template % layer_conf
                    layer_name = '%s.map' % layer_conf['geocode']
                    layer_path = layer_path_disease % layer_name

                    include_layer = include_template % {
                        'disease': disease,
                        'layer_name': layer_name,
                        'city_name': layer_conf['city_name']
                    }

                    self.include_layers[disease][state_name] += include_layer

                    self.generate(
                        template=self.layer_template,
                        parameters=layer_conf,
                        output_file_path=layer_path
                    )

    def create_map(self):
        """

        :return:
        """
        # save mapfile

        # save individual layers
        for disease, states_layer in self.layers.items():
            # save mapfile with all cities
            mapfile_name = self.mapfile_name % disease
            mapfile_path = self.path['local_mapfile_dir'] % mapfile_name
            ms_mapfile_path = self.path['mapserver_mapfile_dir'] % mapfile_name
            disease_title = disease.title()

            ms_config = {
                'include_layers': ''.join(
                    self.include_layers[disease].values()
                ),
                'ms_error_path': self.path['mapserver_error'],
                'ms_cgi_path': self.path['mapserver_cgi'] % ms_mapfile_path,
                'shp_path': self.path['mapserver_shapefile_dir'],
                'extent': self.extent_country,
                'mapfile_name': 'INFO_DENGUE',
                'wms_srs': self.wms_srs_country,
                'crs_proj': self.crs_proj_country,
                'disease': disease,
                'disease_title': disease_title
            }

            self.generate(
                template=self.map_template,
                parameters=ms_config,
                output_file_path=mapfile_path
            )
