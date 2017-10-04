# coding=utf-8
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
# local
from .views import (
    AboutPageView, ContactPageView, JoininPageView, MapaDengueView,
    MapaMosquitoView, PartnersPageView
)

admin.autodiscover()

urlpatterns = [
    # local
    url(r'^mapadengue/$', MapaDengueView.as_view(), name='mapadengue'),
    url(r'^mapamosquito/$', MapaMosquitoView.as_view(), name='mapamosquito'),
    url(r'^informacoes/$', AboutPageView.as_view(), name='about'),
    url(r'^contato/$', ContactPageView.as_view(), name='contact'),
    url(r'^participe/$', JoininPageView.as_view(), name='joinin'),
    url(r'^partners/$', PartnersPageView.as_view(), name='partners'),
    # apps
    url(r'', include('dados.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^dbf/', include('dbf.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
