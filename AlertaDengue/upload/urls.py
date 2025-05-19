from django.urls import path, re_path

from . import views

app_name = "upload"
urlpatterns = [
    re_path(r"^sinan/$", views.SINANDashboard.as_view(), name="sinan"),
    re_path(
        r"^sinan/overview/(?P<sinan_upload_id>[^/]+)/?$",
        views.SINANOverview.as_view(),
        name="sinan",
    ),
    re_path(
        r"^sinan/overview-charts-data/?$",
        views.overview_charts_limit_offset,
        name="overview_charts_limit_offset",
    ),
    re_path(
        r"^sinan/status/(?P<sinan_upload_id>[^/]+)$",
        views.SINANStatus.as_view(),
        name="sinan_status",
    ),
    re_path(
        r"^sinan/get-user-uploads/$",
        views.get_user_uploads,
        name="sinan_get_user_uploads",
    ),
    re_path(
        r"^sinan/file-card/$", views.SINANUpload.as_view(), name="sinan_file"
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
    re_path(
        r"^sinan/residues/(?P<upload_id>[^/]+)/?$",
        views.sinan_download_residues_csv,
        name="sinan_residues",
    ),
]
