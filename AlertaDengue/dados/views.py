# coding: utf8
from django.shortcuts import render
from django.views.generic.base import TemplateView, View
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.http import HttpResponse, StreamingHttpResponse
from dados import models as M
import json


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        messages.info(self.request, 'O site do projeto Alerta Dengue está em construção.')
        return context

class SinanCasesView(View):
    def get(self, request, year):
        assert int(year) in [2010, 2011, 2012, 2013]
        cases = "{\"type\":\"FeatureCollection\", \"features\":["
        if int(year) == 2010:
            dados = M.Dengue_2010.objects.geojson()
           # print(cases[0].geojson)
        elif int(year) == 2011:
            dados = M.Dengue_2011.objects.geojson()
        elif int(year) == 2012:
            dados = M.Dengue_2012.objects.geojson()
        elif int(year) == 2013:
            dados = M.Dengue_2013.objects.geojson()
        else:
            dados = []
        for c in dados[:10]:
            cases += "{\"type\":\"Feature\",\"geometry\":" + c.geojson + ", \"properties\":{}},"
        cases = cases[:-1] + "]}"
        #json.loads(cases)
        return HttpResponse(cases, content_type="application/json")