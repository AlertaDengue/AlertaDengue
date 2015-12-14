from unittest import TestCase
from dados import dbdata
import pandas as pd
import datetime


class TestLoadAlerta(TestCase):
    def setUp(self):
        self.series = dbdata.load_series(330330)

    def test_load(self):
        self.assertIsInstance(self.series, dict)
        self.assertIn('casos_est', self.series['global'].keys())
        self.assertIn('casos', self.series['global'].keys())
        self.assertGreater(len(self.series), 0)

    def test_casos_are_ints(self):
        self.assertIsInstance(self.series['global']['casos'][0], pd.np.int64, '{}'.format(self.series['global']['casos']))
        self.assertIsInstance(self.series['global']['casos_est'][0], pd.np.int64, '{}'.format(self.series['global']['casos_est']))
        self.assertIsInstance(self.series['global']['casos_est_min'][0], pd.np.int64, '{}'.format(self.series['global']['casos_est_min']))
        self.assertIsInstance(self.series['global']['casos_est_max'][0], pd.np.int64, '{}'.format(self.series['global']['casos_est_max']))

    def test_dia_is_date(self):
        self.assertIsInstance(self.series['global']['dia'][0], datetime.date, '{}'.format(type(self.series['global']['dia'][0])))

    def test_alerta_is_between_0_and_3(self):
        self.assertEqual(max(self.series['global']['alerta']), 3)
        self.assertEqual(min(self.series['global']['alerta']), 0)

    def test_get_city_alert(self):
        alert, current, case_series, last_year, obs_case_series, min_max_est = dbdata.get_city_alert(330330)
        self.assertIsInstance(alert, pd.np.int64)
        self.assertIsInstance(current, pd.np.int64)
        self.assertIsInstance(case_series, list)
        self.assertIsInstance(last_year, pd.np.int64)
        self.assertIsInstance(obs_case_series, list)
        self.assertIsInstance(min_max_est, tuple)

