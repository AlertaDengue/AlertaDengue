from django.urls import path

from .views import NotificationListView

app_name = "internal"

urlpatterns = [
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notifications",
    ),
]
