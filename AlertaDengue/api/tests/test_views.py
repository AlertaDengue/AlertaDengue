from django.test import TestCase

try:
    from django.urls import reverse  # django 2
except ModuleNotFoundError:
    # django old version
    from django.core.urlresolvers import reverse


# local
from .. import settings

import django
import io
import os
import pandas as pd
import unittest


class TestApiView(TestCase):
    def setUp(self):
        settings.DATA_DIR = os.path.dirname(__file__)

    def test_notification_reduced_csv_view(self):
        """

        :return:
        """
        response = self.client.get(
            reverse('api:notif_reduced'), {
                'state_abv': 'RJ',
                'chart_type': 'disease'
            }
        )
        self.assertEqual(response.status_code, 200)

    def test_alert_mrj(self):
        # test epidemic start week missing
        response = self.client.get(
            reverse('api:alert_city_rj'), {
                'disease': 'dengue',
                'format': 'json'
            }
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        assert result['error_message'] == 'Epidemic start week sent is empty.'

        # test json format
        response = self.client.get(
            reverse('api:alert_city_rj'), {
                'disease': 'dengue',
                'format': 'json',
                'ew_start': '1',
                'ew_end': '50',
                'e_year': '2017'
            }
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()

        for r in result:
            assert 201701 <= r['se'] <= 201750

        # test csv format
        response = self.client.get(
            reverse('api:alert_city_rj'), {
                'disease': 'dengue',
                'format': 'csv',
                'ew_start': '1',
                'ew_end': '50',
                'e_year': '2017'
            }
        )
        self.assertEqual(response.status_code, 200)
        buffer = io.BytesIO(response.content)
        df = pd.read_csv(buffer)
        assert all(201701 <= df['se']) and all(df['se'] <= 201750)


if __name__ == '__main__':
    django.setup()
    unittest.main()
