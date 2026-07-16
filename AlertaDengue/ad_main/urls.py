from typing import cast

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic import RedirectView

admin.autodiscover()


def status(_request):
    return JsonResponse({"status": "ok"})


static_url = cast(str, settings.STATIC_URL)
static_root = cast(str, settings.STATIC_ROOT)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pwa.urls")),
    re_path(r"^accounts/profile/$", RedirectView.as_view(url="/")),
    re_path(r"^accounts/", include("django.contrib.auth.urls")),
    path("api-auth/", include("rest_framework.urls")),
    # apps
    path(r"", include("dados.urls")),
    re_path(r"^admin/doc/", include("django.contrib.admindocs.urls")),
    re_path(r"^api/", include("api.urls")),
    re_path(r"^status/$", status),
    *static(static_url, document_root=static_root),
]
