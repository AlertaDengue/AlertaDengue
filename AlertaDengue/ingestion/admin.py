from __future__ import annotations

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from ingestion.models import Run, RunRollback, RunStatus
from ingestion.rollback import (
    RollbackValidationError,
    execute_rollback,
    find_previous_completed_run,
    preview_rollback,
)


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
        "rows_failed",
        "rows_duplicate",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "uf", "disease", "source_format")
    search_fields = ("id", "source_path", "filename", "sha256")
    ordering = ("-created_at",)
    readonly_fields = ("rollback_link",)

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "<uuid:run_id>/rollback/",
                self.admin_site.admin_view(self.rollback_view),
                name="ingestion_run_rollback",
            ),
        ]
        return custom_urls + urls

    @admin.display(description="Rollback")
    def rollback_link(self, obj: Run) -> str:
        if obj.status != RunStatus.COMPLETED:
            return "Available only for completed runs."
        latest = (
            Run.objects.filter(
                status=RunStatus.COMPLETED,
                uf=obj.uf,
                disease=obj.disease,
            )
            .order_by("-created_at")
            .first()
        )
        if latest is None or latest.pk != obj.pk:
            return "Available only for the latest completed run."
        url = reverse("admin:ingestion_run_rollback", args=[obj.pk])
        return format_html('<a href="{}">Preview rollback</a>', url)

    def rollback_view(
        self,
        request: HttpRequest,
        run_id: str,
    ) -> HttpResponse:
        """Show a preview, then require explicit POST confirmation."""
        run = get_object_or_404(Run, pk=run_id)
        if not self.has_change_permission(request, run):
            raise PermissionDenied
        try:
            restore_run = find_previous_completed_run(run)
            preview = preview_rollback(run, restore_run)
        except RollbackValidationError as exc:
            self.message_user(request, str(exc), messages.ERROR)
            return redirect("admin:ingestion_run_change", run.pk)

        if request.method == "POST":
            if request.POST.get("confirm") != "rollback":
                self.message_user(
                    request,
                    "Rollback was not confirmed.",
                    messages.WARNING,
                )
                return redirect("admin:ingestion_run_change", run.pk)
            try:
                result = execute_rollback(run, restore_run)
            except RollbackValidationError as exc:
                self.message_user(request, str(exc), messages.ERROR)
                return redirect("admin:ingestion_run_change", run.pk)
            self.message_user(
                request,
                f"Rollback completed: {result.deleted} deleted, "
                f"{result.restored} restored.",
                messages.SUCCESS,
            )
            return redirect("admin:ingestion_run_change", run.pk)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "run": run,
            "restore_run": restore_run,
            "preview": preview,
            "title": "Confirm SINAN ingestion rollback",
        }
        return TemplateResponse(
            request,
            "admin/ingestion/run/rollback_confirmation.html",
            context,
        )


@admin.register(RunRollback)
class RunRollbackAdmin(admin.ModelAdmin):
    """Read-only audit log for ingestion rollback operations."""

    list_display = (
        "id",
        "current_run",
        "restore_run",
        "status",
        "rows_deleted",
        "rows_restored",
        "created_at",
        "finished_at",
    )
    list_filter = ("status",)
    readonly_fields = tuple(field.name for field in RunRollback._meta.fields)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: RunRollback | None = None,
    ) -> bool:
        return request.method in (
            "GET",
            "HEAD",
        ) and super().has_view_permission(
            request,
            obj,
        )
