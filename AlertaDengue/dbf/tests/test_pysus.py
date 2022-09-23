import collections.abc
from datetime import date, timedelta

import numpy as np
import pandas as pd
from dbf.pysus import COL_TO_RENAME, PySUS, add_se, calc_birth_date
from django.test import TestCase


class Test_LoadPySUS(TestCase):
    def setUp(self):
        year = "2016"
        disease = "zika"
        pysus = PySUS(year, disease)

        self.df = pysus.get_data(year, disease)

    def test_get_data(self):
        """
        Check if dataframe contain the expected fields.
        RESUL_PCR field is missing in PySUS data from ZIKA disease.
        """
        self.assertIsInstance(self.df, pd.DataFrame)
        self.assertIn("resul_pcr", self.df.columns)
        self.assertEquals(list(COL_TO_RENAME.values()), list(self.df.columns))

    def test_calc_birth_date(self):
        """
        Check return of birthday date and dtypes are datetime.
        DT_NASC field is missing in PySUS data.
        The value is taken from DT_NOTIFIC field.
        """
        age_dec = 4043
        value = date(2016, 3, 15)
        days_x_year = 43 * 365
        birth_fake = np.array(date(1973, 3, 26), dtype="object")
        birthday = calc_birth_date(value, age_dec)
        birth_date = value - timedelta(days=days_x_year)

        # self.assertIsInstance(age_dec, np.float64)
        self.assertIsInstance(value, date)
        self.assertIsInstance(birth_date, date)
        self.assertEqual(birthday, birth_fake)

    def test_add_se(self):
        """
        Checks if epiweek is converted and inserted into se_notific fields.
        """
        epiweek = add_se(self.df.dt_notific)
        self.assertIsInstance(epiweek, (collections.abc.Sequence, np.ndarray))
        self.assertIn(52, epiweek)
        # self.assertIn("201608", epiweek)

    def test_parse_dataframe(self):
        pass

    def test_upsert_to_pgsql(self):
        pass
