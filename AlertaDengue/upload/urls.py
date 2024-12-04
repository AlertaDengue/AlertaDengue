from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r"^sinan/$", views.SINANUpload.as_view(), name="sinan_upload"),
    re_path(
        r"^sinan/success/$",
        views.SINANUploadSuccessful.as_view(),
        name="sinan_success",
    ),
    re_path(
        r"^chunked_upload/?$",
        views.SINANChunkedUploadView.as_view(),
        name="api_chunked_upload",
    ),
    re_path(
        r"^chunked_upload_complete/?$",
        views.SINANChunkedUploadCompleteView.as_view(),
        name="api_chunked_upload_complete",
    ),
]
