from datetime import datetime
from rasterio.features import rasterize
from rasterio.transform import from_origin

import fiona
import geopy.distance
import os
import numpy as np
import rasterio
import rasterio.mask


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

    raster_src.close()
