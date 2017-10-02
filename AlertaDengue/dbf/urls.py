from django.conf.urls import url

from . import views

app_name = "dbf"

urlpatterns = [
    url(r"^upload/success/$", views.UploadSuccessful.as_view(),
        name="upload_successful"),
    url(r"^upload/$", views.Upload.as_view(), name="upload"),
    url(r'^chunked_upload/?$', views.DBFChunkedUploadView.as_view(),
        name='api_chunked_upload'),
    url(r'^chunked_upload_complete/?$',
        views.DBFChunkedUploadCompleteView.as_view(),
        name='api_chunked_upload_complete'),
]
