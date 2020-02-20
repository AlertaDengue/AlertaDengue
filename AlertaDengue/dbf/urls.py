from django.conf.urls import re_path

from . import views

app_name = "dbf"

urlpatterns = [
    re_path(
        r"^upload/success/$",
        views.UploadSuccessful.as_view(),
        name="upload_successful",
    ),
    re_path(r"^upload/$", views.Upload.as_view(), name="upload"),
    re_path(
        r'^chunked_upload/?$',
        views.DBFChunkedUploadView.as_view(),
        name='api_chunked_upload',
    ),
    re_path(
        r'^chunked_upload_complete/?$',
        views.DBFChunkedUploadCompleteView.as_view(),
        name='api_chunked_upload_complete',
    ),
]
