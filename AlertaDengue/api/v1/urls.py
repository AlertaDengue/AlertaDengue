"""Routing for the public REST API v1 surface."""

from django.urls import path

from api.v1.views import PublicAPIRootView

app_name = "v1"

urlpatterns = [path("", PublicAPIRootView.as_view(), name="root")]
