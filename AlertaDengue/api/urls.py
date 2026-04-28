from django.urls import include, path, re_path

from .views import AlertCityView, EpiYearWeekView, NotificationReducedCSV_View

app_name = "api"

urlpatterns = [
    re_path(
        r"^notif_reduced$",
        NotificationReducedCSV_View.as_view(),
        name="notif_reduced",
    ),
    re_path(r"^alertcity", AlertCityView.as_view(), name="alertcity"),
    re_path(
        r"^epi_year_week$",
        EpiYearWeekView.as_view(),
        name="epi_year_week",
    ),
    path("internal/", include("api.internal.urls")),
]
