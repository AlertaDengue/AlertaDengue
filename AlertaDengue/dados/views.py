# coding: utf8
from django.shortcuts import render, redirect
from django.views.generic.base import TemplateView, View
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.http import HttpResponse, StreamingHttpResponse
from dados import models as M
import random
import json


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        messages.info(self.request, 'O site do projeto Alerta Dengue está em construção.')
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
        print ("chegou aqui")
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
        print(type(dados[0].dt_notific))
        print ("chegou aqui", sample, dados[0].dt_notific)
        for c in random.sample(list(dados), int(len(dados)*sample)):
            print(c)
            cases += "{\"type\":\"Feature\",\"geometry\":" + c.geojson + ", \"properties\":{\"data\":\""+c.dt_notific.isoformat()+"\"}},"
        cases = cases[:-1] + "]}"
        #json.loads(cases)
        return HttpResponse(cases, content_type="application/json")
