# coding=utf-8
import json

from django.core.urlresolvers import reverse
from django.test import TestCase

class TestAlertaPageView(TestCase):
    def setUp(self):
        self.url = reverse('alerta')
        self.response = self.client.get(self.url)

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

    def test_semena(self):
        semana = '20'
        self.assertEqual(self.response.context['semana'], semana)

