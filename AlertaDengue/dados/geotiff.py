from rasterio.features import rasterize
from rasterio.transform import from_origin

import geopy.distance
import os
import numpy as np
import rasterio


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