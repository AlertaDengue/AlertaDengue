"""Routing for the public REST API v1 surface."""

from django.urls import path

from api.v1.views import (
    PublicAlertCityView,
    PublicAPIRootView,
    PublicEpiYearWeekView,
    PublicNotificationReducedCSVView,
)

app_name = "v1"

urlpatterns = [
    path("", PublicAPIRootView.as_view(), name="root"),
    path("alert-city/", PublicAlertCityView.as_view(), name="alert_city"),
    path(
        "epi-year-week/", PublicEpiYearWeekView.as_view(), name="epi_year_week"
    ),
    path(
        "notifications/reduced.csv",
        PublicNotificationReducedCSVView.as_view(),
        name="notification_reduced_csv",
    ),
]
