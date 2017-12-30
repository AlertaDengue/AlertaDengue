from datetime import datetime
from glob import glob
# local
from dados.dbdata import STATE_INITIAL, CID10, db_engine
from dados.dbdata import NotificationResume as notif

from .geodf import extract_boundaries
from .geotiff import get_key_from_file_name, get_date_from_file_name
from .settings import *

import geopandas as gpd
import numpy as np
import os
import pyproj
import sh


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
    """

    """
    layers = []
    map_config = {}
    path = {}
    templates = {}

    mapfile_name = None
    layer_height = 400

    # http://all-geo.org/volcan01010/2012/11/change-coordinates-with-pyproj/
    # LatLon with WGS84 datum used by GPS units and Google Earth
    projections = {
        'wgs84': pyproj.Proj("+init=EPSG:4326"),
        'grs80': pyproj.Proj("+init=EPSG:2154")
    }
    crs_proj_country = 'epsg:2154'
    wms_srs_country = crs_proj_country.upper()

    # boundaries in epsg:2154
    bounds = (0, 0, 0, 0)
    extent_country = stringfy_boundaries(bounds=bounds, sep=' ')

    def __init__(self, **kwargs):
        """

        :param kwargs:
        """
        if kwargs:
            for kw, values in kwargs.items():
                setattr(self, kw, values)

        # configuration
        self.layers = []
        self.templates = {
            'map': get_template_content('map.map'),
            'layer': '',
            'url': (
                    settings.MAPSERVER_URL + '?' +
                    'map=/maps/%(type)s/%(map_class)s.map&' +
                    'SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&' +
                    'STYLES=&CRS=%(crs_url)s&BBOX=%(bbox)s&' +
                    'WIDTH=%(width)s&HEIGHT=%(height)s&FORMAT=%%(format)s&' +
                    'LAYERS=%(layer_name)s'
            ),
            'include_layer': (
                    '  INCLUDE "layers/%(include_map_class)s/' +
                    '%(include_layer_filename)s"  # ' +
                    '%(include_layer_name)s'
            )
        }
        self.path = {
            'shapefile_dir': SHAPEFILE_PATH,
            'raster_dir': RASTER_PATH,
            'local_mapfile_dir': MAPFILE_PATH,
            'mapserver_error': MAPSERVER_LOG_PATH,
            'mapserver_cgi': MAPSERVER_URL + '?map=map.map&',
            'mapserver_shapefile_dir': '/shapefiles',
            'mapserver_mapfile_dir': '/maps'
        }

        # Getting general info geo from Brazil
        gdf_country = gpd.GeoDataFrame.from_file(
            os.path.join(self.path['shapefile_dir'], '%s.shp' % 'UFEBRASIL')
        )

        # boundaries in epsg:2154
        self.bounds = transform_boundaries(
            bounds=extract_boundaries(gdf_country),
            proj_from=self.projections['grs80'],
            proj_to=self.projections['wgs84']
        )

        self.extent_country = stringfy_boundaries(bounds=self.bounds, sep=' ')

    def prepare_images(self):
        pass

    def prepare_folders(self):
        # check if mapserver folder exists
        if not os.path.exists(self.path['local_mapfile_dir']):
            os.mkdir(self.path['local_mapfile_dir'])

        # check if mapserver conf folder exists
        mapserver_conf_dir_path = os.path.join(
            self.path['local_mapfile_dir'], 'conf'
        )

        if not os.path.exists(mapserver_conf_dir_path):
            conf_dir = os.path.join(
                os.path.dirname(__file__),
                'templates', 'mapfile', 'conf'
            )
            sh.cp('-R', conf_dir, self.path['local_mapfile_dir'])

    def create_files(self):
        self.prepare_folders()
        self.prepare_images()
        self.create_layers()
        self.create_map()

    def create_layer(self, layer_config: dict):
        pass

    def create_layers(self):
        self.create_layer(None)

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

    def include_layer(self, layer_conf):
        """

        :param layer_conf:
        :return:
        """
        self.layers.append(self.templates['include_layer'] % layer_conf)


class MapFileAlert(MapFile):
    alert_colors = [
        '#00FF00',
        '#FFFF00',
        '#FF9900',
        '#FF0000',
    ]

    map_class = None

    def __init__(self, map_class, **kwargs):
        super(MapFileAlert, self).__init__(**kwargs)

        self.map_class = map_class
        self.map_config['type'] = 'alert'
        self.map_config['map_class'] = map_class

        self.templates.update({
            'layer': get_template_content(
                'layer_%s.map' % self.map_config['type']
            ),
        })

        self.path['local_mapfile_dir'] = os.path.join(
            self.path['local_mapfile_dir'], self.map_config['type']
        )

        self.path['mapserver_mapfile_dir'] = os.path.join(
            self.path['mapserver_mapfile_dir'], self.map_config['type']
        )

        mapfile_name = '%s.map' % self.map_class
        mapfile_path = os.path.join(
            self.path['local_mapfile_dir'], mapfile_name
        )

        ms_mapfile_path = os.path.join(
            self.path['mapserver_mapfile_dir'], mapfile_name
        )
        self.path['mapserver_cgi'] = (
            MAPSERVER_URL + ('?map=%s.map&' % ms_mapfile_path)
        )

        self.map_config.update({
            'error_path': self.path['mapserver_error'],
            'cgi_path': self.path['mapserver_cgi'],
            'shape_dir_path': self.path['mapserver_shapefile_dir'],
            'extent': self.extent_country,
            'name': 'INFO_DENGUE_%s' % self.map_class,
            'wms_srs': self.wms_srs_country,
            'crs_proj': self.crs_proj_country,
            'map_class': self.map_class,
            'map_class_title': self.map_class.title(),
            'datetime': '%s' % datetime.now(),
            'file_path': mapfile_path
        })

    def create_layer(self, layer_conf):
        """

        :return:
        """
        layer_path_map_class = os.path.join(
            self.path['local_mapfile_dir'], 'layers', self.map_class
        )

        if not os.path.exists(layer_path_map_class):
            os.makedirs(layer_path_map_class)

        # layer_content = self.layer_template % layer_conf
        layer_conf['name'] = '%s.map' % layer_conf['geocode']
        layer_path = os.path.join(layer_path_map_class, layer_conf['name'])

        layer_conf.update({
            'include_map_class': self.map_class,
            'include_layer_filename': layer_conf['name'],
            'include_layer_name': layer_conf['city_name'],
            'datetime': '%s' % datetime.now()
        })

        self.include_layer(layer_conf)
        self.generate(
            template=self.templates['layer'],
            parameters=layer_conf,
            output_file_path=layer_path
        )

    def create_layers(self):
        """

        :return:
        """
        sql_template = '''
        SELECT geocodigo, nome 
        FROM "Dengue_global"."Municipio" 
        WHERE uf = '%s'
        ORDER BY nome;
        '''
        cities = {}
        alerts = {}

        for state_name in STATE_INITIAL.values():
            with db_engine.connect() as conn:
                sql = sql_template % state_name
                result = conn.execute(sql).fetchall()
                cities.update(dict(result))

            cities_alert = notif.get_cities_alert_by_state(
                state_name, self.map_class
            )

            alerts.update(dict(
                cities_alert[['municipio_geocodigo', 'level_alert']].values
            ))

        for geocode, city_name in cities.items():
            # getting shapefile settings
            shapefile_path = os.path.join(
                self.path['shapefile_dir'], '%s.shp' % geocode
            )

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
            alert_color = (
                self.alert_colors[alert_level] if 0 <= alert_level <= 3 else
                '#DFDFDF'  # gray
            )

            layer_name = city_name.upper().replace(' ', '_')

            layer_conf = {
                'map_class': self.map_class,
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
                'height': self.layer_height,
                'datetime': '%s' % datetime.now()
            }

            self.create_layer(layer_conf)

    def create_map(self):
        """

        :return:
        """
        self.map_config['include_layers'] = '\n'.join(self.layers)
        self.generate(
            template=self.templates['map'],
            parameters=self.map_config,
            output_file_path=self.map_config['file_path']
        )


class MapFileMeteorological(MapFile):
    meteorological_class = None

    def __init__(self, map_class, **kwargs):
        super(MapFileMeteorological, self).__init__(**kwargs)
        self.map_config['type'] = 'meteorological'
        self.map_class = map_class

        self.templates.update({
            'layer': get_template_content(
                'layer_%s.map' % self.map_config['type']
            ),
        })

        self.path['local_mapfile_dir'] = os.path.join(
            self.path['local_mapfile_dir'], self.map_config['type']
        )

        self.path['mapserver_mapfile_dir'] = os.path.join(
            self.path['mapserver_mapfile_dir'], self.map_config['type']
        )

        mapfile_name = '%s.map' % self.map_class
        mapfile_path = os.path.join(
            self.path['local_mapfile_dir'], mapfile_name
        )

        ms_mapfile_path = os.path.join(
            self.path['mapserver_mapfile_dir'], mapfile_name
        )
        self.path['mapserver_cgi'] = (
                MAPSERVER_URL + ('?map=%s.map&' % ms_mapfile_path)
        )

        self.map_config.update({
            'error_path': self.path['mapserver_error'],
            'cgi_path': self.path['mapserver_cgi'],
            'shape_dir_path': self.path['mapserver_shapefile_dir'],
            'extent': self.extent_country,
            'name': 'INFO_DENGUE_%s' % self.map_class,
            'wms_srs': self.wms_srs_country,
            'crs_proj': self.crs_proj_country,
            'map_class': self.map_class,
            'map_class_title': self.map_class.title(),
            'datetime': '%s' % datetime.now(),
            'file_path': mapfile_path
        })

    def prepare_images(self):
        """

        :return:
        """
        for k, data_range in RASTER_METEROLOGICAL_DATA_RANGE.items():
            path_search = os.path.join(
                self.path['raster_dir'],
                'meteorological', 'country', k, '*'
            )

            for raster_file_path in glob(path_search):
                raster_name = raster_file_path.split(os.sep)[-1]

                if not raster_name[-3:] == 'tif':
                    continue

                raster_key = get_key_from_file_name(raster_name)

                vmin = data_range[0]
                vmax = data_range[1]

                print(raster_key, vmin, vmax)

    def create_layers(self):
        data_range = RASTER_METEROLOGICAL_DATA_RANGE

        geocode = 1
        rasters = {}
        city_name = ''

        for raster_name, src in rasters.items():
            raster_file_name = '%s_%s' % (geocode, raster_name)
            layer_name = '%s.map' % geocode

            raster_title = get_key_from_file_name(raster_name, False)
            raster_key = raster_title.lower()

            vmin = data_range[raster_key][0]
            vmax = data_range[raster_key][1]

            layer_conf = {
                'geocode': geocode,
                'city_name': city_name.upper().replace(' ', '_'),
                'layer_name': layer_name,
                'rgb': '#FF9900',
                'wms_srs': self.wms_srs,
                'crs_proj': self.crs_proj,
                'raster_path': raster_file_name,
                'vmin': vmin,
                'vmax': vmax,
                'raster_title': raster_title
            }
