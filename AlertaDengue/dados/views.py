# coding: utf8
from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView, View
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.http import HttpResponse, StreamingHttpResponse
from dados import models as M
import random
import json
import os
import datetime
from time import mktime
import csv
from collections import defaultdict
from django.conf import settings

class AlertaPageView(TemplateView):
    template_name = 'alerta.html'
    def get_context_data(self, **kwargs):
        context = super(AlertaPageView, self).get_context_data(**kwargs)
        series = load_series()
        casos_ap = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        messages.info(self.request, "Foram relatados {} novos casos na última Semana.".format(32))
        context.update({
            'casos_por_ap': json.dumps(casos_ap),
        })
        return context

class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        messages.info(self.request, 'O site do projeto Alerta Dengue está em construção.')
        series = load_series()
        context.update({
            'season_alert': json.dumps([{"y": 0, "marker":{"symbol":"url(/static/mosquito_peq.png)"}} if v == 1 else v for v in series['season']]),
            'casos': json.dumps(series['casos']),
            'epidemia_alert': json.dumps([{"y": 2, "marker":{"symbol":"url(/static/mosquito_peq.png)"}} if v == 1 else v for v in series['epidemia']]),
            'transmissao_alert': json.dumps([{"y": 1, "marker":{"symbol":"url(/static/mosquito_peq.png)"}} if v == 1 else v for v in series['transmissao']]),
        })
        return context

class MapaDengueView(TemplateView):
    template_name = 'mapadengue.html'

    def get_context_data(self, **kwargs):
        context = super(MapaDengueView, self).get_context_data(**kwargs)
        return context

class MapaMosquitoView(TemplateView):
    template_name = 'mapamosquito.html'

    def get_context_data(self, **kwargs):
        context = super(MapaMosquitoView, self).get_context_data(**kwargs)
        return context

class HistoricoView(TemplateView):
    template_name = 'historico.html'

    def get_context_data(self, **kwargs):
        context = super(HistoricoView, self).get_context_data(**kwargs)
        series = load_series()
        context.update({
            'xvalues': json.dumps(series['dia']),
            'tweets': json.dumps(series['twits']),
            'temp': json.dumps(series['tmin']),
            'casos': json.dumps(series['casos']),
        })
        return context

class AboutPageView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super(AboutPageView, self).get_context_data(**kwargs)
        messages.info(self.request, 'O site do projeto Alerta Dengue está em construção.')
        return context

class ContactPageView(TemplateView):
    template_name = 'contact.html'

    def get_context_data(self, **kwargs):
        context = super(ContactPageView, self).get_context_data(**kwargs)
        messages.info(self.request, 'O site do projeto Alerta Dengue está em construção.')
        return context

class SinanCasesView(View):
    def get(self, request, year, sample):
        sample = int(sample)
        try:
            assert int(year) in [2010, 2011, 2012, 2013]
        except AssertionError:
            messages.error(self.request, 'O projeto conté dados apenas dos anos 2010 a 2013.')

        sample = 1 if sample == 0 else sample/100.
        #print ("chegou aqui")
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

        if len(dados) < 5500:
            sample = 1
        #print(type(dados[0].dt_notific))
        #print ("chegou aqui", sample, dados[0].dt_notific)
        for c in random.sample(list(dados), int(len(dados)*sample)):
            #print(c)
            cases += "{\"type\":\"Feature\",\"geometry\":" + c.geojson + ", \"properties\":{\"data\":\""+c.dt_notific.isoformat()+"\"}},"
        cases = cases[:-1] + "]}"
        #json.loads(cases)
        return HttpResponse(cases, content_type="application/json")


def load_series():
    series = defaultdict(lambda: [])
    with open(os.path.join(settings.DATA_DIR, 'dengueclimatw2010-2013.csv')) as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            for k, v in row.items():
                series[k].append(v)
    series['dia'] = [int(mktime(datetime.datetime.strptime(d, "%d%b%Y").timetuple())) for d in series['dia']]
    series['twits'] = [float(i) if i != "NA" else None for i in series['twits']]
    series['tmin'] = [float(i) if i != "NA" else None for i in series['tmin']]
    series['casos'] = [float(i) if i != "NA" else None for i in series['casos']]
    series['season'] = [int(float(t) >= 3.7) if t != "NA" else None for t in series['t24']]
    series['transmissao'] = [int(float(rt) > 1) if rt != "NA" else None for rt in series['Rt']]
    series['epidemia'] = [int(t > 157) if t is not None else None for t in series['twits']]
    #print(series['dia'])
    return series
