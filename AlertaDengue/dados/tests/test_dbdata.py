from unittest import TestCase
from .. import dbdata
import datetime


class TestLoadAlerta(TestCase):
    def setUp(self):
        self.cidade = 3303302
        self.series = dbdata.load_series(self.cidade)

    def test_load(self):
        self.assertIsInstance(self.series, dict)
        self.assertIn('casos_est', self.series[str(self.cidade)].keys())
        self.assertIn('casos', self.series[str(self.cidade)].keys())
        self.assertGreater(len(self.series), 0)

    def test_get_cities(self):
        """

        :return:
        """
        cities = dbdata.get_cities()
        assert cities[3304557] == 'Rio de Janeiro'

    def test_casos_are_ints(self):
        self.assertIsInstance(
            self.series[str(self.cidade)]['casos'][0],
            int,
            '{}'.format(self.series[str(self.cidade)]['casos']),
        )
        self.assertIsInstance(
            self.series[str(self.cidade)]['casos_est'][0],
            int,
            '{}'.format(self.series[str(self.cidade)]['casos_est']),
        )
        self.assertIsInstance(
            self.series[str(self.cidade)]['casos_est_min'][0],
            int,
            '{}'.format(self.series[str(self.cidade)]['casos_est_min']),
        )
        self.assertIsInstance(
            self.series[str(self.cidade)]['casos_est_max'][0],
            int,
            '{}'.format(self.series[str(self.cidade)]['casos_est_max']),
        )

    def test_dia_is_date(self):
        self.assertIsInstance(
            self.series[str(self.cidade)]['dia'][0],
            datetime.date,
            '{}'.format(type(self.series[str(self.cidade)]['dia'][0])),
        )

    def test_alerta_is_between_0_and_3(self):
        self.assertEqual(max(self.series[str(self.cidade)]['alerta']), 3)
        self.assertEqual(min(self.series[str(self.cidade)]['alerta']), 0)

    def test_get_city_alert(self):
        (
            alert,
            SE,
            case_series,
            last_year,
            obs_case_series,
            min_max_est,
            dia,
            ptr1,
        ) = dbdata.get_city_alert(3303302)
        self.assertIsInstance(alert, int)
        self.assertIsInstance(SE, int, SE)
        self.assertIsInstance(case_series, list)
        self.assertIsInstance(last_year, int)
        self.assertIsInstance(obs_case_series, list)
        self.assertIsInstance(min_max_est, tuple)
        self.assertIsInstance(dia, datetime.date)


class TestMunicipio(TestCase):
    def test_get_active_cities(self):
        muns = dbdata.get_all_active_cities()
        self.assertIsInstance(muns, list)
        self.assertGreater(len(muns), 0)
        self.assertIn((3303302, 'Niterói'), muns)
