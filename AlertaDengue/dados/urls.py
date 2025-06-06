from dados.dbdata import STATE_NAME
from django.shortcuts import redirect
from django.urls import re_path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

# local
from .views import (
    AboutPageView,
    AlertaMainView,
    AlertaMunicipioPageView,
    AlertaStateView,
    ChartsMainView,
    DataPublicServicesPageView,
    GeoJsonView,
    GeoTiffView,
    JoininPageView,
    ReportCityView,
    ReportStateData,
    ReportStateView,
    ReportView,
    SinanCasesView,
    TeamPageView,
    download_technical_report_pdf,
)


def redirect_alerta_dengue(request, state):
    return redirect("dados:alerta_uf", state=state, disease="dengue")


def redirect_alert_city_dengue(request, geocodigo):
    return redirect(
        "dados:alerta_cidade", geocodigo=geocodigo, disease="dengue"
    )


app_name = "dados"

state_abbv = "|".join(state for state in STATE_NAME.keys())

__disease = "(?P<disease>dengue|chikungunya|zika)"
__state_abbv = f"(?P<state>{state_abbv})"
__regional_id = r"(?P<regional_id>\d{5})"
__geocode = r"(?P<geocodigo>\d{7})"
__geocode_ = r"(?P<geocode>\d{7})"
__year = r"(?P<year>\d{4})"
__month = r"(?P<month>\d{2})"
__day = r"(?P<day>\d{2})"
__e_week = r"(?P<e_week>\d{2})"
__year_week = r"(?P<year_week>\d{6})"
__report_type = "(?P<report_type>city|state)"


urlpatterns = [
    re_path(
        r"^alerta/%s/%s$" % (__state_abbv, __disease),
        cache_page(60 * 60)(AlertaStateView.as_view()),
        name="alerta_uf",
    ),
    re_path(r"^$", cache_page(60 * 60)(AlertaMainView.as_view()), name="main"),
    re_path(
        r"^chartshome/{}$".format(__state_abbv),
        cache_page(60 * 60)(ChartsMainView.as_view()),
        name="chartshome",
    ),
    re_path(
        r"^informacoes/$",
        cache_page(60 * 60 * 60 * 24)(AboutPageView.as_view()),
        name="about",
    ),
    re_path(
        r"^download_technical_report_pdf/$",
        download_technical_report_pdf,
        name="download_technical_report_pdf",
    ),
    re_path(
        r"^equipe/$",
        cache_page(60 * 60 * 60 * 24)(TeamPageView.as_view()),
        name="team",
    ),
    re_path(
        r"^participe/$",
        cache_page(60 * 60 * 60 * 24)(JoininPageView.as_view()),
        name="joinin",
    ),
    re_path(
        r"^services/(?P<service>maps|api)?$",
        DataPublicServicesPageView.as_view(),
        name="data_public_services",
    ),
    re_path(
        r"^services/(?P<service>maps|tutorial)?$",
        DataPublicServicesPageView.as_view(),
        name="data_public_services",
    ),
    re_path(
        r"^services/(?P<service>maps|tutorial)/(?P<service_type>R)$",
        DataPublicServicesPageView.as_view(
            template_name="services_tutorial_R.html"
        ),
        name="services_tutorial_R",
    ),
    re_path(
        r"^tutorial_api_r/",
        TemplateView.as_view(
            template_name="components/tutorial/notebook-API-R-en.html"
        ),
        name="tutorial_api_R",
    ),
    re_path(
        r"^services/(?P<service>maps|tutorial)/(?P<service_type>Python)$",
        DataPublicServicesPageView.as_view(
            template_name="services_tutorial_Python.html"
        ),
        name="services_tutorial_Python",
    ),
    re_path(
        r"^tutorial_api_python/",
        TemplateView.as_view(
            template_name="components/tutorial/notebook-API-Python-en.html"
        ),
        name="tutorial_api_python",
    ),
    re_path(
        r"^services/(?P<service>maps|api)/(?P<service_type>doc)$",
        DataPublicServicesPageView.as_view(),
        name="data_public_services_type",
    ),
    re_path(
        r"^alerta/%s[/]?$" % __state_abbv,
        cache_page(60 * 60 * 8)(redirect_alerta_dengue),
    ),  # Caches the view for the specified number of seconds (8 hours)
    re_path(
        r"^alerta/%s[/]?$" % __geocode,
        cache_page(60 * 60 * 8)(redirect_alert_city_dengue),
    ),  # Caches the view for the specified number of seconds (8 hours).
    re_path(
        r"^alerta/%s/%s$" % (__geocode, __disease),
        cache_page(60 * 60 * 8)(AlertaMunicipioPageView.as_view()),
        name="alerta_cidade",
    ),  # Caches the view for the specified number of seconds (8 hours)
    re_path(
        r"^sinan/(\d{4})/(\d{1,2})",
        cache_page(60 * 60 * 60 * 24)(SinanCasesView.as_view()),
        name="sinan",
    ),
    re_path(
        r"^geotiff/%s/%s/$" % (__geocode, __disease),
        cache_page(60 * 60 * 60 * 24)(GeoTiffView.as_view()),
        name="geotiff",
    ),
    re_path(
        r"^geojson/%s/%s/$" % (__geocode, __disease),
        cache_page(60 * 60 * 60 * 24)(GeoJsonView.as_view()),
        name="geojson",
    ),
    re_path(
        r"^report/$",
        cache_page(60 * 60 * 60 * 24)(ReportView.as_view()),
        name="report",
    ),
    re_path(
        r"^report/{}/{}$".format(__state_abbv, __report_type),
        ReportView.as_view(),
        name="report_filter",
    ),
    re_path(
        r"^report/{}/{}/{}$".format(__state_abbv, __geocode_, __year_week),
        cache_page(60 * 60)(ReportCityView.as_view()),
        name="report_city",
    ),
    re_path(
        r"^report/{}/{}$".format(__state_abbv, __year_week),
        cache_page(60 * 60)(ReportStateView.as_view()),
        name="report_state",
    ),
    re_path(
        r"^fetchdata/{}/{}/{}$".format(
            __state_abbv, __regional_id, __year_week
        ),
        ReportStateData.as_view(),
        name="fetchdata",
    ),
]
