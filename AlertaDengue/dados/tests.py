# coding=utf-8
import json

from django.core.urlresolvers import reverse
from django.test import TestCase

class TestAlertaPageView(TestCase):
    def setUp(self):
        self.url = reverse('alerta')

    def test_casos_por_ap(self):
        response = self.client.get(self.url)
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
        self.assertEqual(json.loads(response.context['casos_por_ap']), casos_por_ap)
