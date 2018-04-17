from django.conf.urls import url
# local
from .views import NotificationReducedCSV_View, AlertCityView, EpiYearWeekView


app_name = "api"

urlpatterns = [
    url(r'^notif_reduced$',
        NotificationReducedCSV_View.as_view(),
        name='notif_reduced'),
    url(r'^alertcity',
        AlertCityView.as_view(),
        name='alertcity'),
    url(r'^epi_year_week$',
        EpiYearWeekView.as_view(),
        name='epi_year_week'),
]
