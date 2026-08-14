from django.urls import path

from api.internal.views import HistoricalAlertListView, NotificationListView

app_name = "internal"

urlpatterns = [
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notifications",
    ),
    path(
        "historical-alerts/",
        HistoricalAlertListView.as_view(),
        name="historical_alerts",
    ),
]
