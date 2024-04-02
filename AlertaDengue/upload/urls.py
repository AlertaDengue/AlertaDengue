from django.urls import path

from . import views

urlpatterns = [
    path("", views.Upload.as_view(), name="upload"),
]
