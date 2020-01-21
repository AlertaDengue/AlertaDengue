from geopandas import GeoDataFrame
import numpy as np


def extract_boundaries(gdf: GeoDataFrame):
    """
    """
    bound_min = gdf.bounds[['minx', 'miny']].min()
    bound_max = gdf.bounds[['maxx', 'maxy']].max()
    bounds = np.array((bound_min, bound_max)).flatten()
    return bounds

