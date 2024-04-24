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
    path(
        "sinan/chunk-upload-file/",
        views.sinan_chunk_uploaded_file,
        name="sinan_chunk_uploaded_file"
    ),
    path(
        "sinan/chunks-to-uf/",
        views.sinan_parse_chunks_to_uf,
        name="sinan_parse_chunks_to_uf"
    ),
    path(
        "sinan/watch-uf-chunks/",
        views.sinan_watch_for_uf_chunks,
        name="sinan_watch_for_uf_chunks"
    ),
]
