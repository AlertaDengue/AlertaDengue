from django.conf.urls import url

from dbf import views

app_name = "dbf"

urlpatterns = [
    url(r"^upload/success/$", views.UploadSuccessful.as_view(),
        name="upload_successful"),
    url(r"^upload/$", views.Upload.as_view(), name="upload"),
]
