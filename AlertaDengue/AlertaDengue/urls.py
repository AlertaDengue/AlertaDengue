# coding=utf-8
from django.conf.urls import patterns, include, url
from django.contrib import admin
from dados.views import DetailsPageView, SinanCasesView, AboutPageView, ContactPageView, JoininPageView, MapaDengueView, \
    MapaMosquitoView, \
    HistoricoView, AlertaPageView, AlertaGeoJSONView, AlertaPageViewMunicipio, CityMapView, get_municipio, \
    AlertaMainView
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView

admin.autodiscover()

urlpatterns = [#'',
               # Examples:
               url(r'^alerta/rio/$', AlertaPageView.as_view(), name='mrj'),
               # url(r'^blog/', include('blog.urls')),
               url(r'^alerta/(?P<geocodigo>\d{7})/$', AlertaPageViewMunicipio.as_view(), name='alerta_cidade'),
               # Cache the main page for a day
               url(r'^$', cache_page(24 * 60 * 60)(AlertaMainView.as_view()), name='main'),
               url('^accounts/profile/$', RedirectView.as_view(url="/")),
               url('^accounts/', include('django.contrib.auth.urls')),
               url(r'^alerta-detalhado/$', DetailsPageView.as_view(), name='home'),
               url(r'^alertageoJSON/$', login_required(AlertaGeoJSONView.as_view()), name='alerta-layer'),
               url(r'^geojson/(?P<geocodigo>\d{7})/$', CityMapView.as_view(), name='mapa'),
               url(r'^getcity/$', get_municipio, name='get_city'),
               url(r'^mapadengue/$', MapaDengueView.as_view(), name='mapadengue'),
               url(r'^mapamosquito/$', MapaMosquitoView.as_view(), name='mapamosquito'),
               url(r'^historico/$', HistoricoView.as_view(), name='historico'),
               url(r'^informacoes/$', AboutPageView.as_view(), name='about'),
               url(r'^contato/$', ContactPageView.as_view(), name='contact'),
               url(r'^participe/$', JoininPageView.as_view(), name='joinin'),
               url(r'^sinan/(\d{4})/(\d{1,2})', SinanCasesView.as_view(), name='sinan'),
               url(r'^admin/', include(admin.site.urls)),
               ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
