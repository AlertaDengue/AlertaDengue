# coding=utf-8
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

admin.autodiscover()

urlpatterns = [
    # '',
    # Examples:
    url(r'', include('dados.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^dbf/', include('dbf.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
