from __future__ import annotations

from django.contrib import admin
from ingestion.models import Run


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "uf",
        "disease",
        "delivery_se",
        "rows_read",
        "rows_parsed",
        "rows_loaded",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "uf", "disease", "source_format")
    search_fields = ("id", "source_path", "filename", "sha256")
    ordering = ("-created_at",)
