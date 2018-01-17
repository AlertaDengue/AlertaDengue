from django.conf.urls import url
# local
from .views import NotificationReducedCSV_View


app_name = "api"

urlpatterns = [
    url(r'^notif_reduced$',
        NotificationReducedCSV_View.as_view(),
        name='notif_reduced'),
]
