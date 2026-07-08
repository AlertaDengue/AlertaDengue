from django.urls import path

from api.internal.views import NotificationListView

app_name = "internal"

urlpatterns = [
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notifications",
    ),
]
