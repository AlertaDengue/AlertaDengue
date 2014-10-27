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
import pandas as pd
import numpy as np

dados_alerta = pd.read_csv(os.path.join(settings.DATA_DIR, 'alertaAPS.csv'), header=0)

class AlertaPageView(TemplateView):
    template_name = 'alerta.html'
    def get_context_data(self, **kwargs):
        context = super(AlertaPageView, self).get_context_data(**kwargs)
        alert, current = get_alert()
        casos_ap = {float(ap.split('AP')[-1]): int(current[current.APS == ap]['casos']) for ap in alert.keys()}
        alerta = {float(k.split('AP')[-1]): v-1 for k, v in alert.items()}
        semana = str(current.SE.iat[-1])[-2:]
        messages.info(self.request, "Foram relatados {} novos casos na Semana Epidemiológica {}.".format(sum(casos_ap.values()), semana))
        context.update({
            'casos_por_ap': json.dumps(casos_ap),
            'alerta': alerta,
            'semana': semana,
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
        aps = list(series.keys())
        aps.sort()
        context.update({
            'APS': aps,
            'xvalues': json.dumps(series['AP1']['dia']),
            'dados': json.dumps(series)
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

def get_alert():
    """
    Read the data and return the alert status of all APs.
    """
    df = dados_alerta
    df.fillna(0, inplace=True)
    last_SE = df.SE.max() #Last epidemiological week
    year = datetime.date.today().year  # Current year
    SE = int(str(last_SE).split(str(year))[-1])  # current epidemiological week
    current = df[df['SE'] == last_SE]  # Current status
    print(current)
    G = df.groupby("APS")
    group_names = G.groups.keys()
    alert = defaultdict(lambda: 0)
    for ap in group_names:
        adf = G.get_group(ap)#.tail()  # only calculates on the series tail
        alert[ap] = adf.cor.iloc[-1]
    return alert, current



def load_series():
    """
    Monta as séries para visualização no site
    """
    series = defaultdict(lambda: defaultdict(lambda: []))
    G = dados_alerta.groupby("APS")
    for ap in G.groups.keys():
        series[ap]['dia'] = [int(mktime(datetime.datetime.strptime(d, "%Y-%m-%d").timetuple())) if isinstance(d, str) else None for d in G.get_group(ap).data]
        series[ap]['tweets'] = [float(i) if not np.isnan(i) else None for i in G.get_group(ap).tweets]
        series[ap]['tmin'] = [float(i) if not np.isnan(i) else None for i in G.get_group(ap).tmin]
        series[ap]['casos'] = [float(i) if not np.isnan(i) else None for i in G.get_group(ap).casos]
        series[ap]['alerta'] = [c-1 if not np.isnan(c) else None for c in G.get_group(ap).cor]
        #print(series['dia'])
    return series

def get_global_series(col, group):
    series = group[col].groups.items()
    ssum = None
    for g, ser in group[col].items():
        if ssum is None:
            ssum = np.array(ser)
        else:
            ssum += np.array(ser)
