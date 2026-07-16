import io
import os
from typing import Final
import unittest

import django
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
import pandas as pd

# local

MRJ_GEOCODE: Final = 3304557


class TestApiView(TestCase):
    def setUp(self):
        setattr(settings, "DATA_DIR", os.path.dirname(__file__))

    def test_notification_reduced_csv_view(self):
        """

        :return:
        """
        response = self.client.get(
            reverse("api:notif_reduced"),
            {"state_abv": "RJ", "chart_type": "disease"},
        )
        self.assertEqual(response.status_code, 200)

    @unittest.skip("Waiting data on database demo.")
    def test_notification_reduced_csv_404_view(self):
        """

        :return:
        """
        response = self.client.get(
            reverse("api:notif_reduced"), {"chart_type": "disease"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.content,
            b"ERROR: The parameter state_abv not found. "
            + b"This parameter should have 2 letter (e.g. RJ).",
        )

    @unittest.skip("Waiting for Rio de Janeiro data on database demo.")
    def test_alert_rj(self):
        geocode = MRJ_GEOCODE
        # test epidemic start week missing
        missing_week_query: dict[str, str | int] = {
            "disease": "dengue",
            "geocode": geocode,
            "format": "json",
        }
        response = self.client.get(
            reverse("api:alertcity"), missing_week_query
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        assert result["error_message"] == "Epidemic start week sent is empty."

        # test json format
        json_query: dict[str, str | int] = {
            "disease": "dengue",
            "geocode": geocode,
            "format": "json",
            "ew_start": 1,
            "ew_end": 50,
            "e_year": 2017,
        }
        response = self.client.get(reverse("api:alertcity"), json_query)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        assert "error_message" not in result

        for r in result:
            assert 201701 <= r["se"] <= 201750

        # test csv format
        csv_query: dict[str, str | int] = {
            "disease": "dengue",
            "geocode": geocode,
            "format": "csv",
            "ew_start": "1",
            "ew_end": "50",
            "e_year": "2017",
        }
        response = self.client.get(reverse("api:alertcity"), csv_query)
        self.assertEqual(response.status_code, 200)
        buffer = io.BytesIO(response.content)
        df = pd.read_csv(buffer)
        assert all(201701 <= df["se"]) and all(df["se"] <= 201750)

    @unittest.skip("Waiting for Curitiba data on database demo.")
    def test_alert_curitiba(self):
        geocode = 4106902
        # test epidemic start week missing
        missing_week_query: dict[str, str | int] = {
            "disease": "dengue",
            "geocode": geocode,
            "format": "json",
        }
        response = self.client.get(
            reverse("api:alertcity"), missing_week_query
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()

        assert result["error_message"] == "Epidemic start week sent is empty."

        # test json format
        json_query: dict[str, str | int] = {
            "disease": "dengue",
            "geocode": geocode,
            "format": "json",
            "ew_start": 1,
            "ew_end": 50,
            "e_year": 2017,
        }
        response = self.client.get(reverse("api:alertcity"), json_query)

        self.assertEqual(response.status_code, 200)

        result = response.json()

        assert "error_message" not in result

        for r in result:
            assert 201701 <= r["SE"] <= 201750

        # test csv format
        csv_query: dict[str, str | int] = {
            "disease": "dengue",
            "geocode": geocode,
            "format": "csv",
            "ew_start": "1",
            "ew_end": "50",
            "e_year": "2017",
        }
        response = self.client.get(reverse("api:alertcity"), csv_query)
        self.assertEqual(response.status_code, 200)
        buffer = io.BytesIO(response.content)
        df = pd.read_csv(buffer)
        assert all(201701 <= df["SE"]) and all(df["SE"] <= 201750)


if __name__ == "__main__":
    django.setup()
    unittest.main()
