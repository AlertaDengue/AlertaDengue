# coding=utf-8
from django.conf.urls import url
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
# local
from .views import (
    DetailsPageView, SinanCasesView, AlertaMRJPageView,
    AlertaGeoJSONView, AlertaMunicipioPageView, get_municipio, AlertaMainView,
    AlertaStateView, GeoTiffView, GeoJsonView, ReportCityView
)


def redirect_alerta_dengue(request, state):
    return redirect('dados:alerta_uf', state=state, disease='dengue')


def redirect_alert_rio_dengue(request):
    return redirect('dados:mrj', disease='dengue')


def redirect_alert_city_dengue(request, geocodigo):
    return redirect(
        'dados:alerta_cidade',
        geocodigo=geocodigo,
        disease='dengue'
    )


app_name = "dados"

__disease = '(?P<disease>dengue|chikungunya|zika)'
__state = '(?P<state>CE|ES|MG|PR|RJ)'
__geocode = '(?P<geocodigo>\d{7})'
__geocode_ = '(?P<geocode>\d{7})'
__year = '(?P<year>\d{4})'
__month = '(?P<month>\d{2})'
__day = '(?P<day>\d{2})'
__e_week = '(?P<e_week>\d{2})'

urlpatterns = [
    url(r'^$', AlertaMainView.as_view(), name='main'),
    url(r'^alerta/%s[/]?$' % __state, redirect_alerta_dengue),
    url(r'^alerta/%s/%s$' % (__state, __disease),
        AlertaStateView.as_view(), name='alerta_uf'),
    url(r'^alerta/rio/$', redirect_alert_rio_dengue),
    url(r'^alerta/rio/%s$' % __disease,
        AlertaMRJPageView.as_view(), name='mrj'),
    url(r'^alerta/%s[/]?$' % __geocode, redirect_alert_city_dengue),
    url(r'^alerta/%s/%s$' % (__geocode, __disease),
        AlertaMunicipioPageView.as_view(), name='alerta_cidade'),
    url(r'^alerta-detalhado/$', DetailsPageView.as_view(), name='home'),
    url(r'^alertageoJSON/$',
        login_required(AlertaGeoJSONView.as_view()), name='alerta-layer'),
    url(r'^getcity/$', get_municipio, name='get_city'),
    url(r'^sinan/(\d{4})/(\d{1,2})', SinanCasesView.as_view(), name='sinan'),
    url(r'^geotiff/%s/%s/$' % (__geocode, __disease),
        GeoTiffView.as_view(), name='geotiff'),
    url(r'^geojson/%s/%s/$' % (__geocode, __disease),
        GeoJsonView.as_view(), name='geojson'),
    url(r'^report/city/%s/%s/%s/$' % (__geocode_, __year, __e_week),
        ReportCityView.as_view(), name='report_city'),
]
