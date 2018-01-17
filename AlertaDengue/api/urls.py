from django.conf.urls import url
# local
from .views import NotificationReducedCSV_View, AlertCityRJView


app_name = "api"

urlpatterns = [
    url(r'^notif_reduced$',
        NotificationReducedCSV_View.as_view(),
        name='notif_reduced'),
    url(r'^alert_city_rj',
        AlertCityRJView.as_view(),
        name='alert_city_rj'),
]
