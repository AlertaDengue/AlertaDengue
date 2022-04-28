import numpy as np
from geopandas import GeoDataFrame


def extract_boundaries(gdf: GeoDataFrame):
    """ """
    bound_min = gdf.bounds[["minx", "miny"]].min()
    bound_max = gdf.bounds[["maxx", "maxy"]].max()
    bounds = np.array((bound_min, bound_max)).flatten()
    return bounds
