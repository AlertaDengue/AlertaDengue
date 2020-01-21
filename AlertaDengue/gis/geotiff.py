from copy import copy
from datetime import datetime
from glob import glob
from rasterio import Affine
from rasterio.features import rasterize
from rasterio.transform import from_origin

#local
from .settings import *
from dados.dbdata import get_cities

import fiona
import geopy.distance
import os
import multiprocessing as mp
import numpy as np
import rasterio
import rasterio.mask
import traceback as tb


def convert_from_shapefile(shapefile, rgb_color):
    """
    
    :param shp: 
    :param rgb_color: 
    :return: 
    """
    shp = shapefile  # alias
    # get coordinates
    coords_1 = shp.bounds[1], shp.bounds[0]

    # coordinate 2 to get height
    coords_2 = shp.bounds[3], shp.bounds[0]

    height = geopy.distance.vincenty(coords_1, coords_2).km
    # coordinate 2 to get width
    coords_2 = shp.bounds[1], shp.bounds[2]

    width = geopy.distance.vincenty(coords_1, coords_2).km

    res_x = (shp.bounds[2] - shp.bounds[0]) / width
    res_y = (shp.bounds[3] - shp.bounds[1]) / height

    out_shape = int(height), int(width)

    transform = from_origin(
        shp.bounds[0] - res_x / 2,
        shp.bounds[3] + res_y / 2,
        res_x, res_y
    )

    shapes = [
        [(geometry['geometry'], color)]
        for k, geometry in shp.items()
        for color in rgb_color
    ]

    # creates raster file
    dtype = rasterio.float64
    fill = np.nan

    raster_args = dict(
        out_shape=out_shape,
        fill=fill,
        transform=transform,
        dtype=dtype,
        all_touched=True
    )

    rasters = [rasterize(shape, **raster_args) for shape in shapes]
    geotiff_path = '/tmp/%s.tif' % np.random.randint(100000, 999999)

    with rasterio.open(
        geotiff_path,
        mode='w',
        crs=shp.crs,
        driver='GTiff',
        # profile='GeoTIFF',
        dtype=dtype,
        count=3,
        width=width,
        height=height,
        nodata=np.nan,
        transform=transform,
        photometric='RGB'
    ) as dst:
        for i in range(1, 4):
            dst.write_band(i, rasters[i - 1])

    with open(geotiff_path, 'rb') as f:
        result = f.read()

    os.remove(geotiff_path)
    return result


def get_key_from_file_name(raster_name, to_lower=True):
    """
    """
    if raster_name[-14:].count('_') == 2:
        raster_key = raster_name[:-15]
    else:
        raster_key = raster_name[:-19]

    if to_lower:
        raster_key = raster_key.lower()

    return raster_key


def get_date_from_file_name(raster_name, to_lower=True):
    """
    """
    if raster_name[-14:].count('_') == 2:
        dt = raster_name[-14:-4]
    else:
        dt = raster_name[-18:-8]

    return datetime.strptime(dt, '%Y_%m_%d')


def mask_raster_with_shapefile(
    shapefile_path: str,
    raster_input_file_path: str,
    raster_output_file_path: str
):
    """

    :param shapefile_path:
    :param raster_input_file_path:
    :param raster_output_file_path:
    :return:
    """
    # using fiona to get coordinates
    with fiona.open(shapefile_path, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]

    raster_src = rasterio.open(raster_input_file_path)

    # https://mapbox.github.io/rasterio/topics/masking-by-shapefile.html

    # make raster mask
    out_image, out_transform = rasterio.mask.mask(
        raster_src, features, crop=True, nodata=np.nan, all_touched=True
    )
    out_meta = raster_src.meta.copy()
    raster_src.close()

    img_type = out_image.dtype
    # cheating
    if img_type == np.float64:
        img_type = np.float64
    elif img_type == np.float32:
        img_type = np.float32

    out_meta.update({
        'driver': "GTiff",
        'height': out_image.shape[1],
        'width': out_image.shape[2],
        'transform': out_transform,
        'dtype': img_type
    })

    with rasterio.open(raster_output_file_path, "w", **out_meta) as dst:
        dst.write(out_image)


def increase_resolution(raster_file_path: str, factor_increase: int):
    """
    References:
    * mapbox.github.io/rasterio/topics/resampling.html#use-decimated-reads

    :param raster_file_path:
    :param factor_increase:
    :return:
    """
    # this method need a integer factor resolution
    res = int(factor_increase)  # alias
    with rasterio.open(raster_file_path) as src:
        image = src.read()

        image_new = np.empty(
            shape=(
                image.shape[0],  # same number of bands
                round(image.shape[1] * res),  # n times resolution
                round(image.shape[2] * res)),  # n times resolution
            dtype=image.dtype
        )

        image = src.read(out=image_new).copy()
        meta = dict(src.profile)

    aff = copy(meta['affine'])
    meta['transform'] = Affine(
        aff.a / res,
        aff.b,
        aff.c,
        aff.d,
        aff.e / res,
        aff.f
    )
    meta['affine'] = meta['transform']
    meta['width'] *= res
    meta['height'] *= res

    with rasterio.open(raster_file_path, "w", **meta) as dst:
        dst.write(image)


class MeteorologicalRasterProcess:
    def __init__(self, raster_class, raster_date, raster_input_file_path):
        self.raster_class = raster_class
        self.raster_date = raster_date
        self.raster_input_file_path = raster_input_file_path

    def __call__(self, geo_info):
        try:
            geocode, city_name = geo_info
            raster_output_dir_path = os.path.join(
                RASTER_PATH, 'meteorological', 'city', self.raster_class,
                str(geocode)
            )

            # create output path if not exists
            if not os.path.exists(raster_output_dir_path):
                os.makedirs(raster_output_dir_path, exist_ok=True)

            # check if shapefile exists
            shapefile_path = os.path.join(
                SHAPEFILE_PATH, '%s.shp' % geocode
            )
            if not os.path.exists(shapefile_path):
                return

            raster_output_file_path = os.path.join(
                raster_output_dir_path,
                '%s.tif' % self.raster_date.strftime('%Y%m%d')
            )

            # apply mask on raster using shapefile by city
            mask_raster_with_shapefile(
                shapefile_path=shapefile_path,
                raster_input_file_path=self.raster_input_file_path,
                raster_output_file_path=raster_output_file_path
            )

            # increase resolution
            increase_resolution(
                raster_file_path=raster_output_file_path,
                factor_increase=RASTER_METEROLOGICAL_FACTOR_INCREASE
            )

            # apply mask on increased resolution raster using shapefile by city
            mask_raster_with_shapefile(
                shapefile_path=shapefile_path,
                raster_input_file_path=raster_output_file_path,
                raster_output_file_path=raster_output_file_path
            )
        except:
            if DEBUG:
                log_path = os.path.join(
                    os.sep, 'tmp', 'raster_%s.log' % self.raster_class
                )
                with open(log_path, 'a') as f:
                    f.write('%s: %s' % (datetime.now(), tb.format_exc()))


class MeteorologicalRaster:
    @staticmethod
    def generate_raster_cities(
        raster_class: str,
        date_start: datetime=None
    ):
        """
        Create raster images by city using as mask a shapefile and background
        a raster file of the whole country.

        Each city can have raster file for datetime regards the datetime from
        the original file (whole country).

        :param raster_class:
        :param date_start:
        :return:
        """
        path_search = os.path.join(
            RASTER_PATH,
            'meteorological', 'country', raster_class, '*'
        )

        cities = get_cities().items()

        n_processes = mp.cpu_count()

        for raster_input_file_path in glob(path_search, recursive=True):
            raster_name = raster_input_file_path.split(os.sep)[-1]

            # filter by tiff format
            if not raster_name[-3:] == 'tif':
                continue

            # filter by date
            raster_date = get_date_from_file_name(raster_name)
            if date_start is not None and raster_date < date_start:
                continue

            # processing
            p = mp.Pool(n_processes)

            p.map(
                MeteorologicalRasterProcess(
                    raster_class, raster_date, raster_input_file_path
                ), cities
            )
            p.close()
            p.join()
