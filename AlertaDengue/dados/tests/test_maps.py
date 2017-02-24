from unittest import TestCase
from dados import maps


class TestMaps(TestCase):
    def test_return_valid_geojson(self):
        maps.get_city_geojson(3304557)
