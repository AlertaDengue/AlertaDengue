from django.test import TestCase
from datetime import datetime

# local
from .. import mapfile
from ..settings import RASTER_METEROLOGICAL_DATA_RANGE
from dados.dbdata import CID10

import numpy as np
import os
import pyproj
import unittest


class TestMapFile(TestCase):
    def setUp(self):
        pass

    def test_stringfy_boundaries(self):
        """

        :return:
        """
        bounds = (1, 2, 3, 4)
        assert mapfile.stringfy_boundaries(bounds=bounds, sep=' ') == '1 2 3 4'

    def test_calc_layer_width_by_boundaries(self):
        """

        :return:
        """
        bounds = (0, 0, 200, 100)
        assert 800 == mapfile.calc_layer_width_by_boundaries(
            bounds=bounds, layer_height=400
        )

    def test_get_template_content(self):
        """

        :return:
        """
        cwd = os.path.dirname(__file__)
        cwd = os.path.dirname(cwd)

        file_path = os.path.join(cwd, 'templates', 'mapfile', 'map.map')
        with open(file_path) as f:
            assert mapfile.get_template_content('map.map') == f.read()

    def test_transform_boundaries(self):
        """

        :return:
        """
        wgs84 = pyproj.Proj("+init=EPSG:4326")
        grs80 = pyproj.Proj("+init=EPSG:2154")

        bounds_from = [-73.99044997, -33.75208127, -28.83590763, 5.27184108]
        # boundaries in epsg:2154
        bounds_to = mapfile.transform_boundaries(
            bounds=bounds_from, proj_from=grs80, proj_to=wgs84
        )
        bounds_assert = [-1.36352984, -5.98409199, -1.36326239, -5.98383341]

        np.testing.assert_allclose(bounds_to, bounds_assert, atol=0.00000001)

    def test_MapFileAlert(self):
        """

        :return:
        """
        for disease in CID10.keys():
            mf = mapfile.MapFileAlert(map_class=disease)
            mf.create_files()

    def test_MapFileMeteorological(self):
        """

        :return:
        """
        date_start = datetime.strptime('2017-01-01', '%Y-%m-%d')

        for c in RASTER_METEROLOGICAL_DATA_RANGE:
            mf = mapfile.MapFileMeteorological(
                map_class=c, date_start=date_start
            )
            mf.create_files()


if __name__ == '__main__':
    unittest.main()
