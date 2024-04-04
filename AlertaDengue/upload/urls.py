from django.urls import path

from . import views

urlpatterns = [
    path("sinan/", views.UploadSINAN.as_view(), name="upload_sinan"),
]
