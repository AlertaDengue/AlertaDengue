# coding=utf-8
from django.conf.urls import include, url
from django.contrib import admin
from django.views.decorators.cache import cache_page
from dados.views import (
    DetailsPageView, SinanCasesView, AboutPageView,
    ContactPageView, JoininPageView, MapaDengueView,
    MapaMosquitoView,
    HistoricoView, AlertaPageView, AlertaGeoJSONView, AlertaPageViewMunicipio,
    CityMapView, get_municipio,
    AlertaMainView, AlertaStateView, NotificationReducedCSV_View,
    PartnersPageView, GeoTiffView
)
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
import dbf.urls

admin.autodiscover()


def redirect_alerta_dengue(request, state):
    return redirect('alerta_uf', state=state, disease='dengue')


def redirect_alert_rio_dengue(request):
    return redirect('mrj', disease='dengue')


def redirect_alert_city_dengue(request, geocodigo):
    return redirect(
        'alerta_cidade',
        geocodigo=geocodigo,
        disease='dengue'
    )

__disease = '(?P<disease>dengue|chikungunya)'
__state = '(?P<state>CE|ES|MG|PR|RJ)'
__geocode = '(?P<geocodigo>\d{7})'

urlpatterns = [
    # '',
    # Examples:
    url(r'^alerta/%s/$' % __state, redirect_alerta_dengue),
    url(r'^alerta/%s/%s$' % (__state, __disease),
        AlertaStateView.as_view(), name='alerta_uf'),
    url(r'^alerta/rio/$', redirect_alert_rio_dengue),
    url(r'^alerta/rio/%s$' % __disease, AlertaPageView.as_view(), name='mrj'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^alerta/%s/$' % __geocode, redirect_alert_city_dengue),
    url(r'^alerta/%s/%s$' % (__geocode, __disease),
        AlertaPageViewMunicipio.as_view(), name='alerta_cidade'),
    url(r'^$', AlertaMainView.as_view(), name='main'),
    url('^accounts/profile/$', RedirectView.as_view(url="/")),
    url('^accounts/', include('django.contrib.auth.urls')),
    url(r'^alerta-detalhado/$', DetailsPageView.as_view(), name='home'),
    url(r'^alertageoJSON/$',
        login_required(AlertaGeoJSONView.as_view()), name='alerta-layer'),
    url(r'^geojson/%s/$' % __geocode,
        cache_page(60 * 60 * 24)(CityMapView.as_view()), name='mapa'),
    url(r'^getcity/$', get_municipio, name='get_city'),
    url(r'^mapadengue/$', MapaDengueView.as_view(), name='mapadengue'),
    url(r'^mapamosquito/$', MapaMosquitoView.as_view(), name='mapamosquito'),
    url(r'^historico/$', HistoricoView.as_view(), name='historico'),
    url(r'^informacoes/$', AboutPageView.as_view(), name='about'),
    url(r'^contato/$', ContactPageView.as_view(), name='contact'),
    url(r'^participe/$', JoininPageView.as_view(), name='joinin'),
    url(r'^partners/$', PartnersPageView.as_view(), name='partners'),
    url(r'^sinan/(\d{4})/(\d{1,2})', SinanCasesView.as_view(), name='sinan'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^dbf/', include(dbf.urls)),
    url(r'^csv/notif_reduced$',
        NotificationReducedCSV_View.as_view(),
        name='notif_reduced'),
    url(r'^geotiff/%s/%s/$' % (__geocode, __disease),
        GeoTiffView.as_view(), name='geotiff'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
