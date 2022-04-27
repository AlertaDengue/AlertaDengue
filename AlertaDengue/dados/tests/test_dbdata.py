import datetime
from unittest import TestCase

from dados import dbdata
from dados.dbdata import RegionalParameters
from dados.tests import legacy  # noqa
from pandas._testing import assert_frame_equal

# Paramaters
cities = [3304557]
year_week_start = 202003
year_week_end = 202003
var_climate = "temp_min"
year_week = 202002
station_id = "SBRJ"


class TestLoadAlerta(TestCase):
    def setUp(self):
        self.cidade = 3303302
        self.series = dbdata.load_series(self.cidade)

    def test_load(self):
        self.assertIsInstance(self.series, dict)
        self.assertIn("casos_est", self.series[str(self.cidade)].keys())
        self.assertIn("casos", self.series[str(self.cidade)].keys())
        self.assertGreater(len(self.series), 0)

    def test_casos_are_ints(self):
        self.assertIsInstance(
            self.series[str(self.cidade)]["casos"][0],
            int,
            "{}".format(self.series[str(self.cidade)]["casos"]),
        )
        self.assertIsInstance(
            self.series[str(self.cidade)]["casos_est"][0],
            int,
            "{}".format(self.series[str(self.cidade)]["casos_est"]),
        )
        self.assertIsInstance(
            self.series[str(self.cidade)]["casos_est_min"][0],
            int,
            "{}".format(self.series[str(self.cidade)]["casos_est_min"]),
        )
        self.assertIsInstance(
            self.series[str(self.cidade)]["casos_est_max"][0],
            int,
            "{}".format(self.series[str(self.cidade)]["casos_est_max"]),
        )

    def test_dia_is_date(self):
        self.assertIsInstance(
            self.series[str(self.cidade)]["dia"][0],
            datetime.date,
            "{}".format(type(self.series[str(self.cidade)]["dia"][0])),
        )

    def test_alerta_is_between_0_and_3(self):
        self.assertEqual(max(self.series[str(self.cidade)]["alerta"]), 3)
        self.assertEqual(min(self.series[str(self.cidade)]["alerta"]), 0)

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
        self.assertIn((3303302, "Niterói"), muns)


class TestReportState(TestCase):
    def test_read_disease_data(self):
        """
        Compare the structure of dataframes
        """

        df_sql_func = legacy.OldReportState._read_disease_data(
            cities, station_id, year_week, var_climate
        )
        df_sql = df_sql_func.iloc[:, 3:12].astype(float)
        df_sql.info()

        df_ibis_func = dbdata.ReportState.read_disease_data(
            cities, station_id, year_week, var_climate
        )

        df_ibis_func.set_index("SE", inplace=True)
        df_ibis = df_ibis_func.iloc[:, 3:12].astype(float)
        df_ibis.info()

        assert_frame_equal(df_sql, df_ibis)


class TestRegionalParameters(TestCase):
    def setUp(self):

        state = "RJ"
        self.state_name = dbdata.STATE_NAME[state]

    def test_load(self):
        pass

    def test_get_regional_names(self):
        """

        :return:
        """
        regional_names = RegionalParameters.get_regional_names(self.state_name)
        self.assertIsNotNone(
            self.state_name, msg="required argument: 'state_name'"
        )
        self.assertIsInstance(regional_names, list)
        self.assertEqual(len(regional_names), 9)

    def test_get_var_climate_info(self):
        """

        :return:
        """
        cities = {3304557: "Rio de Janeiro"}

        var_climate = RegionalParameters.get_var_climate_info(cities.keys())

        self.assertIsInstance(var_climate, tuple)
        self.assertIn("temp_min", var_climate)
        self.assertEqual(var_climate[0], "SBGL")

    def test_get_cities(self):
        """

        :return:
        """
        cities = RegionalParameters.get_cities()

        self.assertIsInstance(cities, dict)
        self.assertEqual(len(cities), 3204)
        self.assertIn("Rio de Janeiro", self.state_name)
        self.assertEqual(cities[3304557], "Rio de Janeiro")
