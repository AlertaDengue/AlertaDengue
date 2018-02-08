from datetime import datetime
from glob import glob
# local
from dados.dbdata import (
    STATE_INITIAL, db_engine, get_cities,
    NotificationResume as notif
)

from .geodf import extract_boundaries
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
    crs_proj_country = 'epsg:4326'
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
                'map=/maps/%(map_type)s/%(map_class)s.map&' +
                'SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&' +
                'STYLES=&CRS=%(crs_url)s&BBOX=%(bbox)s&' +
                'WIDTH=%(width)s&HEIGHT=%(height)s&FORMAT=%%(format)s&' +
                'LAYERS=%(layer_name)s'
            ),
            'include_layer': (
                '  INCLUDE "layers/%(map_class)s/%(file_name)s"  # %(title)s'
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
        """
        gdf_country = gpd.GeoDataFrame.from_file(
            os.path.join(self.path['shapefile_dir'], '%s.shp' % 'UFEBRASIL')
        )

        # boundaries in epsg:2154
        self.bounds = transform_boundaries(
            bounds=extract_boundaries(gdf_country),
            proj_from=self.projections['grs80'],
            proj_to=self.projections['wgs84']
        )
        """
        self.bounds = [-1.36352984, -5.98409199, -1.36326239, -5.98383341]

        self.extent_country = stringfy_boundaries(bounds=self.bounds, sep=' ')

    def prepare_folders(self):
        # check if mapserver folder exists
        if not os.path.exists(self.path['local_mapfile_dir']):
            os.makedirs(self.path['local_mapfile_dir'], exist_ok=True)

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
        self.create_layers()
        self.create_map()

    def create_layer(self, layer_conf: dict):
        if not os.path.exists(layer_conf['dir_path']):
            os.makedirs(layer_conf['dir_path'], exist_ok=True)

        layer_path = os.path.join(
            layer_conf['dir_path'], layer_conf['file_name']
        )

        self.include_layer(layer_conf)
        self.generate(
            template=self.templates['layer'],
            parameters=layer_conf,
            output_file_path=layer_path
        )

    def create_layers(self):
        self.create_layer(None)

    def create_map(self):
        self.map_config['include_layers'] = '\n'.join(self.layers)
        self.generate(
            template=self.templates['map'],
            parameters=self.map_config,
            output_file_path=self.map_config['file_path']
        )

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
        self.map_config['map_type'] = 'alert'
        self.map_config['map_class'] = map_class

        self.templates.update({
            'layer': get_template_content(
                'layer_%s.map' % self.map_config['map_type']
            ),
        })

        self.path['local_mapfile_dir'] = os.path.join(
            self.path['local_mapfile_dir'], self.map_config['map_type']
        )

        self.path['mapserver_mapfile_dir'] = os.path.join(
            self.path['mapserver_mapfile_dir'], self.map_config['map_type']
        )

        mapfile_name = '%s.map' % self.map_class
        mapfile_path = os.path.join(
            self.path['local_mapfile_dir'], mapfile_name
        )

        ms_mapfile_path = os.path.join(
            self.path['mapserver_mapfile_dir'], mapfile_name
        )
        self.path['mapserver_cgi'] = (
            MAPSERVER_URL + ('?map=%s&' % ms_mapfile_path)
        )

        self.map_config.update({
            'map_class': self.map_class,
            'title': self.map_class.title(),
            'name': 'INFO_DENGUE_%s' % self.map_class,
            'date_time': '%s' % datetime.now(),
            # paths
            'error_path': self.path['mapserver_error'],
            'cgi_path': self.path['mapserver_cgi'],
            'shape_dir_path': self.path['mapserver_shapefile_dir'],
            # projections and extensions
            'file_path': mapfile_path,
            'extent': self.extent_country,
            'wms_srs': self.wms_srs_country,
            'crs_proj': self.crs_proj_country,
        })

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
                # general information
                'map_class': self.map_class,
                'geocode': geocode,
                'title': city_name,
                'name': layer_name,
                'rgb': alert_color,
                'date_time': '%s' % datetime.now(),
                # projections and extensions
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
                # paths
                'file_name': '%s.map' % geocode,
                'dir_path': os.path.join(
                    self.path['local_mapfile_dir'],
                    'layers', self.map_class
                )
            }

            self.create_layer(layer_conf)


class MapFileMeteorological(MapFile):
    """

    """
    def __init__(
        self, map_class: str, date_start: datetime=None, **kwargs
    ):
        super(MapFileMeteorological, self).__init__(**kwargs)
        self.map_config['map_type'] = 'meteorological'
        self.map_class = map_class
        self.date_start = date_start

        self.templates.update({
            'layer': get_template_content(
                'layer_%s.map' % self.map_config['map_type']
            ),
        })

        self.path['local_mapfile_dir'] = os.path.join(
            self.path['local_mapfile_dir'], self.map_config['map_type']
        )

        self.path['mapserver_mapfile_dir'] = os.path.join(
            self.path['mapserver_mapfile_dir'], self.map_config['map_type']
        )

        mapfile_name = '%s.map' % self.map_class
        mapfile_path = os.path.join(
            self.path['local_mapfile_dir'], mapfile_name
        )

        ms_mapfile_path = os.path.join(
            self.path['mapserver_mapfile_dir'], mapfile_name
        )
        self.path['mapserver_cgi'] = (
                MAPSERVER_URL + ('?map=%s&' % ms_mapfile_path)
        )
        self.path['mapserver_shapefile_dir'] = os.path.join(
            os.sep, 'tiffs', 'meteorological', 'city', self.map_class
        )

        self.map_config.update({
            # general information
            'name': 'INFO_DENGUE_%s' % self.map_class.upper(),
            'map_class': self.map_class,
            'title': self.map_class.upper(),
            'date_time': '%s' % datetime.now(),
            # projections and extensions
            'extent': self.extent_country,
            'wms_srs': self.wms_srs_country,
            'crs_proj': self.crs_proj_country,
            # paths
            'file_path': mapfile_path,
            'error_path': self.path['mapserver_error'],
            'cgi_path': self.path['mapserver_cgi'],
            'shape_dir_path': self.path['mapserver_shapefile_dir'],
        })

    def create_layers(self):
        data_range = RASTER_METEROLOGICAL_DATA_RANGE[self.map_class]

        # get a list with geo codes and city names from available states
        for geocode, city_name in get_cities().items():
            raster_name = None
            raster_date = None

            # check the last raster file available by city
            raster_dir_path = os.path.join(
                RASTER_PATH, 'meteorological', 'city', self.map_class,
                str(geocode),
            )
            search_path = os.path.join(
                raster_dir_path, '*'
            )

            for raster_file_path in glob(search_path, recursive=True):
                # filter by tiff format
                if not raster_file_path[-3:] == 'tif':
                    continue
                _raster_name = raster_file_path.split(os.sep)[-1]
                _raster_date = datetime.strptime(_raster_name, '%Y%m%d.tif')

                if raster_date is None or raster_date < _raster_date:
                    raster_name = _raster_name
                    raster_date = _raster_date

            # skip if no file found
            if raster_name is None:
                continue

            # layer configuration definition
            layer_name = city_name.upper().replace(' ', '_')
            layer_title = city_name.title()
            vmin, vmax = data_range

            layer_conf = {
                # general information
                'map_class': self.map_class,
                'geocode': geocode,
                'name': layer_name,
                'rgb': '#FF9900',
                'title': layer_title,
                'date_time': str(datetime.now()),
                # projection and data range
                'wms_srs': self.map_config['wms_srs'],
                'crs_proj': self.map_config['crs_proj'],
                'vmin': vmin,
                'vmax': vmax,
                # path
                'file_name': '%s.map' % geocode,
                'data_name': '%s.tif' % raster_date.strftime('%Y%m%d'),
                'dir_path': os.path.join(
                    self.path['local_mapfile_dir'],
                    'layers', self.map_class
                )
            }

            self.create_layer(layer_conf)
