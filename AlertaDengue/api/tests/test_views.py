from django.test import TestCase

try:
    from django.urls import reverse  # django 2
except ModuleNotFoundError:
    # django old version
    from django.core.urlresolvers import reverse


# local
from .. import settings
from ..views import NotificationReducedCSV_View

import django
import os
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
        pass


if __name__ == '__main__':
    django.setup()
    unittest.main()
