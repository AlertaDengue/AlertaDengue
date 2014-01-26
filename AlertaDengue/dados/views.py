from django.shortcuts import render
from django.views.generic.base import TemplateView, View
from django.contrib import messages
from django.http import HttpResponse, StreamingHttpResponse
from dados import models as M


class HomePageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)
        messages.info(self.request, 'O site do projeto Alerta Dengue está em construção.')
        return context

class SinanCasesView(View):
    def get(self, request, year):
        assert int(year) in [2010, 2011, 2012, 2013]
        if int(year) == 2010:
            cases = M.Dengue_2010.objects.geojson()
           # print(cases[0].geojson)
        elif int(year) == 2011:
            cases = M.Dengue_2011.objects.geojson()
        else:
            cases = []
        return StreamingHttpResponse([c.geojson for c in cases])