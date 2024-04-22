from django.urls import path

from . import views

urlpatterns = [
    path("sinan/", views.UploadSINAN.as_view(), name="upload_sinan"),
    path(
        "sinan/csv-preview/",
        views.sinan_check_csv_columns,
        name="sinan_csv_preview"
    ),
    path(
        "sinan/upload-file/",
        views.sinan_upload_file,
        name="sinan_upload_file"
    ),
    path(
        "sinan/process-file/",
        views.ProcessSINAN.as_view(),
        name="sinan_process_file"
    ),
]
