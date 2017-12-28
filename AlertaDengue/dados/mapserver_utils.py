# coding: utf-8

# # Mapserver / Mapfile

# In[1]:

from django.conf import settings
# local
from . import dbdata
from .dbdata import STATE_INITIAL, CID10, db_engine

import geopandas as gpd
import numpy as np
import os
import pyproj


def extract_boundaries(gdf: gpd.GeoDataFrame):
    """
    """
    bound_min = gdf.bounds[['minx', 'miny']].min()
    bound_max = gdf.bounds[['maxx', 'maxy']].max()
    bounds = np.array((bound_min, bound_max)).flatten()
    return bounds


def stringfy_boundaries(bounds: np.array, sep=' '):
    str_boundaries = [str(v) for v in bounds]
    return sep.join(str_boundaries)


def calc_layer_width_by_boundaries(bounds: np.array, layer_height: int = 400):
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


def generate_alert_mapfiles():
    """

    :return:
    """
    # ## Setting variables

    shp_path = settings.SHAPEFILE_PATH
    local_mapfile_dir = settings.MAPFILE_PATH

    ms_shp_path = '/shapefiles'
    ms_error_path = settings.MAPSERVER_LOG_PATH
    ms_cgi_path = settings.MAPSERVER_URL + '?map=%s&'
    ms_mapfile_name = '%s.map'
    ms_mapfile_dir = '/maps/%s'

    state_initials = STATE_INITIAL

    # ### Define Brazil's boundaries

    # Getting general info geo from Brazil
    gdf_brazil = gpd.GeoDataFrame.from_file(
        os.path.join(shp_path, '%s.shp' % 'UFEBRASIL')
    )

    # http://all-geo.org/volcan01010/2012/11/change-coordinates-with-pyproj/
    # LatLon with WGS84 datum used by GPS units and Google Earth
    wgs84 = pyproj.Proj("+init=EPSG:4326")
    grs80 = pyproj.Proj("+init=EPSG:2154")

    # boundaries in epsg:2154
    bounds = extract_boundaries(gdf_brazil)

    # boundaries in epsg:4326
    bounds[0], bounds[1] = pyproj.transform(grs80, wgs84, bounds[0], bounds[1])
    bounds[2], bounds[3] = pyproj.transform(grs80, wgs84, bounds[2], bounds[3])

    extent_brazil = stringfy_boundaries(bounds=bounds, sep=' ')

    crs_proj_brazil = 'epsg:2154'
    wms_srs_brazil = crs_proj_brazil.upper()

    diseases = tuple(CID10.keys())

    alert_colors = [
        '#00FF00',
        '#FFFF00',
        '#FF9900',
        '#FF0000',
    ]

    # ## Mapfile

    # ### Templates

    # mapfile templates
    mapfile_template = get_template_content('mapfile_template.map')
    mapfile_layer_template = get_template_content('mapfile_layer_template.map')

    # ### Generating the mapfile

    sql_template = '''
    SELECT geocodigo, nome, uf 
    FROM "Dengue_global"."Municipio" 
    WHERE uf = '%s'
    ORDER BY nome;
    '''

    # prepare mapfile
    layer_height = 400

    layers = {}
    state_bounds = {}

    template_url = (
        settings.MAPSERVER_URL + '?' +
        'map=/maps/dengue.map&' +
        'SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&' +
        'STYLES=&CRS=%(crs_url)s&BBOX=%(bbox)s&' +
        'WIDTH=%(width)s&HEIGHT=%(height)s&FORMAT=%%(format)s&' +
        'LAYERS=%(layer_name)s'
    )
    url_cities = []

    for disease in diseases:
        layers[disease] = {}
        state_bounds[disease] = {}

        # layers by state
        for state_name in state_initials.keys():
            with db_engine.connect() as conn:
                sql = sql_template % state_name
                result = conn.execute(sql).fetchall()

            cities_alert = dbdata.NotificationResume.get_cities_alert_by_state(
                state_name, disease
            )

            alerts = dict(
                cities_alert[['municipio_geocodigo', 'level_alert']].values
            )

            layers[disease][state_name] = []

            for geocode, city_name, state_country in result:
                # getting shapefile settings
                shapefile_path = os.path.join(shp_path, '%s.shp' % geocode)

                if not os.path.exists(shapefile_path):
                    continue

                gdf = gpd.GeoDataFrame.from_file(shapefile_path)

                crs_proj = gdf.crs['init']
                wms_srs = crs_proj.upper()
                bounds = extract_boundaries(gdf)

                layer_bbox = stringfy_boundaries(bounds=bounds, sep=',')
                layer_width = calc_layer_width_by_boundaries(
                    bounds=bounds, layer_height=layer_height
                )

                alert_level = alerts[geocode] if geocode in alerts else -1
                # print(alert_level)
                alert_color = (
                    alert_colors[alert_level] if 0 <= alert_level <= 3 else
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
                        crs_proj if not crs_proj.upper() == 'EPSG:4326' else
                        'CRS:84'
                    ),
                    'bbox': layer_bbox,
                    'width': layer_width,
                    'height': layer_height
                }

                layers[disease][state_name] += [layer_conf]

                url_cities.append(
                    template_url % layer_conf
                )

    # save mapfile

    include_layers = {}
    include_template = (
        '    INCLUDE "layers/%(disease)s/%(layer_name)s"  # %(city_name)s\n'
    )

    # save individual layers
    for disease, states_layer in layers.items():
        include_layers[disease] = {}

        layer_path_disease = local_mapfile_dir % (
                'layers/%s/%%s' % disease
        )

        disease_title = disease.title()

        if not os.path.exists(layer_path_disease):
            os.makedirs(layer_path_disease)

        for state_name, layers_conf in states_layer.items():
            include_layers[disease][state_name] = ''
            for layer_conf in layers_conf:
                layer_content = mapfile_layer_template % layer_conf
                layer_name = '%s.map' % layer_conf['geocode']
                layer_path = layer_path_disease % layer_name

                include_layer = include_template % {
                    'disease': disease,
                    'layer_name': layer_name,
                    'city_name': layer_conf['city_name']
                }

                # @deprecated: this check was done before
                if not os.path.exists(
                        os.path.join(shp_path, '%s.shp' % layer_conf['geocode'])
                ):
                    include_layer = '#' + include_layer

                include_layers[disease][state_name] += include_layer

                with open(layer_path, 'w') as f:
                    f.write(layer_content)

        # save mapfile with all cities
        mapfile_name = ms_mapfile_name % disease
        mapfile_path = local_mapfile_dir % mapfile_name
        ms_mapfile_path = ms_mapfile_dir % mapfile_name

        ms_config = {
            'include_layers': ''.join(include_layers[disease].values()),
            'ms_error_path': ms_error_path,
            'ms_cgi_path': ms_cgi_path % ms_mapfile_path,
            'shp_path': ms_shp_path,
            'extent': extent_brazil,
            'mapfile_name': 'INFO_DENGUE',
            'wms_srs': wms_srs_brazil,
            'crs_proj': crs_proj_brazil,
            'disease': disease,
            'disease_title': disease_title
        }

        mapfile_content = mapfile_template % ms_config

        print('Saving ', mapfile_path, 'file ...')
        with open(mapfile_path, 'w') as f:
            f.write(mapfile_content)


if __name__ == '__main__':
    generate_alert_mapfiles()