from api.internal.views import NotificationListView
from django.urls import path

app_name = "internal"

urlpatterns = [
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notifications",
    ),
]
