from django.conf.urls import re_path

# local
from .views import AlertCityView, EpiYearWeekView

app_name = "api"

urlpatterns = [
    re_path(r"^alertcity", AlertCityView.as_view(), name="alertcity"),
    re_path(
        r"^epi_year_week$", EpiYearWeekView.as_view(), name="epi_year_week"
    ),
]
