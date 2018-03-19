# coding=utf-8
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
# local
from .views import (
    AboutPageView, ContactPageView, JoininPageView, MapaDengueView,
    MapaMosquitoView, PartnersPageView
)

admin.autodiscover()

try:
    url_admin = url(r'^admin/', admin.site.urls)  # django 2
except:
    url_admin = url(r'^admin/', include(admin.site.urls))  # django old version


urlpatterns = [
    # local
    url(r'^mapadengue/$', MapaDengueView.as_view(), name='mapadengue'),
    url(r'^mapamosquito/$', MapaMosquitoView.as_view(), name='mapamosquito'),
    url(r'^informacoes/$', AboutPageView.as_view(), name='about'),
    url(r'^contato/$', ContactPageView.as_view(), name='contact'),
    url(r'^participe/$', JoininPageView.as_view(), name='joinin'),
    url(r'^partners/$', PartnersPageView.as_view(), name='partners'),
    url(r'^accounts/profile/$', RedirectView.as_view(url="/")),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    # apps
    url(r'', include('dados.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url_admin,
    url(r'^dbf/', include('dbf.urls')),
    url(r'^api/', include('api.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

