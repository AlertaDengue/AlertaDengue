from django.conf.urls import url

from . import views

app_name = "dbf"

urlpatterns = [
    url(r"^upload/$", views.upload, name="upload")
]
