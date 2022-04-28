# coding=utf-8
import json
import os
import unittest
from unittest import skip

from django.conf import settings
from django.test import TestCase
from django.urls import reverse


class TestAlertaStaticPageView(TestCase):
    def test_about(self):
        response = self.client.get(reverse("dados:about"))
        self.assertEqual(response.status_code, 200)

    def test_team(self):
        response = self.client.get(reverse("dados:team"))
        self.assertEqual(response.status_code, 200)

    def test_joinin(self):
        response = self.client.get(reverse("dados:joinin"))
        self.assertEqual(response.status_code, 200)

    def test_data_public_services(self):
        response = self.client.get(reverse("dados:data_public_services"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("dados:data_public_services", kwargs={"service": "maps"})
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("dados:data_public_services", kwargs={"service": "api"})
        )
        self.assertEqual(response.status_code, 200)

    def test_data_public_services_type(self):
        response = self.client.get(
            reverse(
                "dados:data_public_services_type",
                kwargs={"service": "maps", "service_type": "doc"},
            )
        )
        self.assertEqual(response.status_code, 200)


@unittest.skip("reason='Issue #334'")
class TestAlertaPageView(TestCase):
    def setUp(self):
        settings.DATA_DIR = os.path.dirname(__file__)
        self.response = self.client.get(reverse("dados:mrj", args=["dengue"]))

    @skip
    def test_casos_por_ap(self):
        casos_por_ap = {
            "1.0": 0,
            "2.1": 18,
            "2.2": 4,
            "3.1": 40,
            "3.2": 6,
            "3.3": 55,
            "4.0": 5,
            "5.1": 6,
            "5.2": 8,
            "5.3": 1,
        }
        self.assertEqual(
            json.loads(self.response.context["casos_por_ap"]), casos_por_ap
        )

    @skip
    def test_alerta(self):
        alerta = {
            1.0: 1,
            2.1: 1,
            2.2: 1,
            3.1: 2,
            3.2: 1,
            3.3: 2,
            4.0: 1,
            5.1: 1,
            5.2: 1,
            5.3: 1,
        }

        self.assertEqual(self.response.context["alerta"], alerta)

    @skip
    def test_novos_casos(self):
        novos_casos = 143
        self.assertEqual(self.response.context["novos_casos"], novos_casos)

    @skip
    def test_series_casos(self):
        series_casos = {
            "1.0": [3, 6, 4, 2, 5, 3, 12, 14, 10, 0, 0, 0],
            "2.1": [6, 15, 15, 26, 23, 37, 83, 48, 36, 21, 20, 18],
            "2.2": [2, 15, 12, 20, 14, 17, 41, 18, 46, 4, 4, 4],
            "3.1": [17, 16, 22, 28, 49, 42, 67, 78, 99, 33, 37, 40],
            "3.2": [10, 5, 11, 25, 15, 21, 29, 36, 36, 5, 6, 6],
            "3.3": [11, 14, 22, 25, 21, 63, 81, 62, 109, 46, 51, 55],
            "4.0": [12, 15, 19, 33, 32, 51, 104, 50, 28, 8, 7, 5],
            "5.1": [17, 26, 39, 42, 49, 73, 184, 101, 73, 8, 7, 6],
            "5.2": [15, 20, 28, 28, 34, 56, 86, 49, 55, 10, 9, 8],
            "5.3": [5, 2, 5, 12, 5, 8, 16, 10, 3, 1, 1, 1],
        }
        self.assertEqual(self.response.context["series_casos"], series_casos)

    @skip
    def test_SE(self):
        SE = 20
        self.assertEqual(self.response.context["SE"], SE)

    @skip
    def test_data1(self):
        data1 = "18 de maio de 2015"
        self.assertEqual(self.response.context["data1"], data1)

    @skip
    def test_data2(self):
        data2 = "24 de maio de 2015"
        self.assertEqual(self.response.context["data2"], data2)

    @skip
    def test_last_year(self):
        last_year = 0
        self.assertEqual(self.response.context["last_year"], last_year)

    @skip
    def test_look_back(self):
        look_back = 12
        self.assertEqual(self.response.context["look_back"], look_back)

    @skip
    def test_total_series(self):
        total_series = (
            "98, 134, 177, 241, 247, 371, 703, 466, 495, 136, 142, 143"
        )
        self.assertEqual(self.response.context["total_series"], total_series)
