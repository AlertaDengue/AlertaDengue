from django.urls import re_path

from . import views

app_name = "upload"
urlpatterns = [
    re_path(r"^sinan/$", views.SINANDashboard.as_view(), name="sinan"),
    re_path(
        r"^sinan/file$",
        views.SINANUpload.as_view(),
        name="sinan_file"
    ),
    re_path(
        r"^sinan/chunked/?$",
        views.SINANChunkedUploadView.as_view(),
        name="sinan_chunked",
    ),
    re_path(
        r"^sinan/chunked/(?P<upload_id>[^/]+)/delete/?$",
        views.SINANChunkedUploadView.as_view(),
        name="sinan_chunked_delete",
    ),
    re_path(
        r"^sinan/chunked/complete/?$",
        views.SINANChunkedUploadCompleteView.as_view(),
        name="sinan_chunked_complete",
    ),
]
