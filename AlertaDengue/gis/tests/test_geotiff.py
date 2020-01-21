from datetime import datetime
from django.test import TestCase
from glob import glob
# local
from ..geotiff import (
    get_date_from_file_name,
    get_key_from_file_name,
    mask_raster_with_shapefile,
    increase_resolution
)
from .. import settings

import os
import numpy as np
import rasterio
import shutil
import unittest


class TestGeoTiff(TestCase):
    def setUp(self):
        self.tiff_names = (
            ('LST_Day_1km', '2017_11_04'),
            ('LST_Night_1km', '2017_03_25', '018'),
            ('NDVI', '2010_12_19'),
            ('Precipitation', '2017_10_03', '354'),
            ('relative_humidity_2m_above_ground', '2016_07_18'),
            ('specific_humidity_2m_above_ground', '2017_11_26')
        )

    def test_get_key_from_file_name(self):
        """

        :return:
        """
        for file_name in self.tiff_names:
            result = get_key_from_file_name(
                '_'.join(file_name) + '.tif'
            )
            assert result == file_name[0].lower()

    def test_date_from_file_name(self):
        """

        :return:
        """
        for file_name in self.tiff_names:
            result = get_date_from_file_name(
                '_'.join(file_name) + '.tif'
            )
            assert result == datetime.strptime(file_name[1], '%Y_%m_%d')

    def test_mask_raster_with_shapefile(self):
        """

        :return:
        """
        shapefile_path = '%s/static/shapefile' % settings.BASE_DIR
        geocode = 3304557
        raster_dir_path = settings.RASTER_PATH

        for k in settings.RASTER_METEROLOGICAL_DATA_RANGE.keys():
            raster_country_dir_path = os.path.join(
                raster_dir_path, 'country', k
            )
            raster_city_dir_path = os.path.join(raster_dir_path, 'city', k)

            for raster_input_file_path in glob(
                os.path.join(raster_country_dir_path, '*')
            ):
                if not raster_input_file_path.endswith('.tif'):
                    continue

                raster_name = raster_input_file_path.split(os.sep)[-1]
                raster_new_name = '%s_%s' % (geocode, raster_name)
                raster_output_file_path = os.path.join(
                    raster_city_dir_path, raster_new_name
                )
                mask_raster_with_shapefile(
                    shapefile_path=shapefile_path,
                    raster_input_file_path=raster_input_file_path,
                    raster_output_file_path=raster_output_file_path
                )

    def test_increase_resolution(self):
        """

        :return:
        """
        raster_name = '3304557_NDVI_2010_09_30.tif'
        factor_increase = 4

        original_raster_file_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), 'data', raster_name
            )
        )
        new_raster_file_path = os.path.join(os.sep, 'tmp', raster_name)

        shutil.copyfile(
            original_raster_file_path, new_raster_file_path
        )

        increase_resolution(
            raster_file_path=new_raster_file_path,
            factor_increase=factor_increase
        )

        res = factor_increase

        with rasterio.open(original_raster_file_path) as src_original:
            with rasterio.open(new_raster_file_path) as src_new:
                profile1 = src_original.profile
                profile2 = src_new.profile

                img1 = src_original.read()
                img2 = src_new.read()

                assert profile1['height'] * res == profile2['height']
                assert profile1['width'] * res == profile2['width']
                assert np.nanmin(img1) == np.nanmin(img2)
                assert np.nanmax(img1) == np.nanmax(img2)
                assert np.nanmean(img1) == np.nanmean(img2)
                assert np.nanmedian(img1) == np.nanmedian(img2)


if __name__ == '__main__':
    unittest.main()
