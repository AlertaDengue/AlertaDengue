# coding=utf-8
import json

from django.core.urlresolvers import reverse
from django.test import TestCase

class TestAlertaPageView(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse('alerta'))

    def test_casos_por_ap(self):
        casos_por_ap = {
            u"1.0": 0,
            u"4.0": 5,
            u"2.2": 4,
            u"3.2": 6,
            u"3.1": 40,
            u"5.3": 1,
            u"2.1": 18,
            u"5.2": 8,
            u"5.1": 6,
            u"3.3": 55,
        }
        self.assertEqual(json.loads(self.response.context['casos_por_ap']), casos_por_ap)

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
             5.3: 1
         }

        self.assertEqual(self.response.context['alerta'], alerta)

    def test_semana(self):
        semana = '20'
        self.assertEqual(self.response.context['semana'], semana)

    def test_novos_casos(self):
        novos_casos = 143
        self.assertEqual(self.response.context['novos_casos'], novos_casos)

    def test_series_casos(self):
        series_casos = {
            '5.1': [17, 25, 37, 40, 45, 66, 160, 84, 57, 6, 6, 6],
            '5.2': [15, 20, 27, 27, 32, 51, 75, 41, 43, 7, 7, 7],
            '5.3': [5, 2, 5, 12, 5, 8, 14, 9, 3, 1, 1, 1],
            '1.0': [3, 6, 4, 2, 5, 3, 11, 12, 8, 0, 0, 0],
            '4.0': [12, 15, 18, 31, 30, 46, 91, 42, 22, 6, 6, 6],
            '3.2': [10, 5, 11, 24, 14, 19, 26, 30, 28, 4, 4, 4],
            '3.3': [11, 14, 21, 24, 20, 57, 71, 52, 85, 32, 32, 32],
            '3.1': [17, 16, 21, 27, 45, 38, 59, 65, 77, 23, 23, 23],
            '2.2': [2, 15, 12, 19, 13, 16, 36, 15, 36, 3, 3, 3],
            '2.1': [6, 15, 15, 25, 22, 34, 73, 40, 28, 15, 15, 15],
        }
        self.assertEqual(self.response.context['series_casos'], series_casos)

    def test_SE(self):
        # TODO: Remove it. It is just int(semana).
        SE = 20
        self.assertEqual(self.response.context['SE'], SE)

    def test_data1(self):
        data1 = '18 de maio de 2015'
        self.assertEqual(self.response.context['data1'], data1)

    def test_data2(self):
        data2 = '24 de maio de 2015'
        self.assertEqual(self.response.context['data2'], data2)


