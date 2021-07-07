from django.urls import re_path
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from dados.dbdata import STATE_NAME

# local
from .views import (
    DetailsPageView,
    SinanCasesView,
    AlertaMRJPageView,
    AlertaGeoJSONView,
    AlertaMunicipioPageView,
    get_municipio,
    AlertaMainView,
    AlertaStateView,
    GeoTiffView,
    GeoJsonView,
    ReportStateView,
    ReportCityView,
    ReportView,
    AboutPageView,
    TeamPageView,
    JoininPageView,
    DataPublicServicesPageView,
)


def redirect_alerta_dengue(request, state):
    return redirect('dados:alerta_uf', state=state, disease='dengue')


def redirect_alert_rio_dengue(request):
    return redirect('dados:mrj', disease='dengue')


def redirect_alert_city_dengue(request, geocodigo):
    return redirect(
        'dados:alerta_cidade', geocodigo=geocodigo, disease='dengue'
    )


app_name = "dados"

STATE_ABBV = '(?P<state>{})'.format(
    '|'.join(state for state in STATE_NAME.keys())
)

__disease = '(?P<disease>dengue|chikungunya|zika)'
__state = STATE_ABBV
__state_extra = STATE_ABBV
__geocode = r'(?P<geocodigo>\d{7})'
__geocode_ = r'(?P<geocode>\d{7})'
__year = r'(?P<year>\d{4})'
__month = r'(?P<month>\d{2})'
__day = r'(?P<day>\d{2})'
__e_week = r'(?P<e_week>\d{2})'
__year_week = r'(?P<year_week>\d{6})'
__report_type = '(?P<report_type>city|state)'

urlpatterns = [
    re_path(r'^$', AlertaMainView.as_view(), name='main'),
    re_path(r'^informacoes/$', AboutPageView.as_view(), name='about'),
    re_path(r'^equipe/$', TeamPageView.as_view(), name='team'),
    re_path(r'^participe/$', JoininPageView.as_view(), name='joinin'),
    re_path(
        r'^services/(?P<service>maps|api)?$',
        DataPublicServicesPageView.as_view(),
        name="data_public_services",
    ),
    re_path(
        r'^services/(?P<service>maps|tutorial)?$',
        DataPublicServicesPageView.as_view(),
        name="data_public_services",
    ),
    re_path(
        r'^services/(?P<service>maps|tutorial)/(?P<service_type>R)$',
        DataPublicServicesPageView.as_view(),
        name="data_public_services_type",
    ),
    re_path(
        r'^services/(?P<service>maps|api)/(?P<service_type>doc)$',
        DataPublicServicesPageView.as_view(),
        name="data_public_services_type",
    ),
    re_path(r'^alerta/%s[/]?$' % __state, redirect_alerta_dengue),
    re_path(
        r'^alerta/%s/%s$' % (__state, __disease),
        AlertaStateView.as_view(),
        name='alerta_uf',
    ),
    re_path(r'^alerta/rio/$', redirect_alert_rio_dengue),
    re_path(
        r'^alerta/rio/%s$' % __disease, AlertaMRJPageView.as_view(), name='mrj'
    ),
    re_path(r'^alerta/%s[/]?$' % __geocode, redirect_alert_city_dengue),
    re_path(
        r'^alerta/%s/%s$' % (__geocode, __disease),
        AlertaMunicipioPageView.as_view(),
        name='alerta_cidade',
    ),
    re_path(r'^alerta-detalhado/$', DetailsPageView.as_view(), name='home'),
    re_path(
        r'^alertageoJSON/$',
        login_required(AlertaGeoJSONView.as_view()),
        name='alerta-layer',
    ),
    re_path(r'^getcity/$', get_municipio, name='get_city'),
    re_path(
        r'^sinan/(\d{4})/(\d{1,2})', SinanCasesView.as_view(), name='sinan'
    ),
    re_path(
        r'^geotiff/%s/%s/$' % (__geocode, __disease),
        GeoTiffView.as_view(),
        name='geotiff',
    ),
    re_path(
        r'^geojson/%s/%s/$' % (__geocode, __disease),
        GeoJsonView.as_view(),
        name='geojson',
    ),
    re_path(r'^report/$', ReportView.as_view(), name='report'),
    re_path(
        r'^report/{}/{}$'.format(__state_extra, __report_type),
        ReportView.as_view(),
        name='report_filter',
    ),
    re_path(
        r'^report/{}/{}/{}$'.format(__state_extra, __geocode_, __year_week),
        ReportCityView.as_view(),
        name='report_city',
    ),
    re_path(
        r'^report/{}/{}$'.format(__state_extra, __year_week),
        ReportStateView.as_view(),
        name='report_state',
    ),
]
