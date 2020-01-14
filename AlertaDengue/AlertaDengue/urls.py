# coding=utf-8
from django.urls import include, path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
    path(r'accounts/profile/', RedirectView.as_view(url="/")),
    path(r'accounts/', include('django.contrib.auth.urls')),
    # apps
    path(r'', include('dados.urls')),
    path(r'admin/doc/', include('django.contrib.admindocs.urls')),
    path(r'dbf/', include('dbf.urls')),
    path(r'api/', include('api.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
