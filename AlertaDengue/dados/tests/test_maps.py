from unittest import TestCase
from AlertaDengue.dados import maps
import geojson




class TestMaps(TestCase):
    def test_return_valid_geojson(self):
        res = maps.get_city_geojson(3304557)
