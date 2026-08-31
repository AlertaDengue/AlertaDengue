from dataclasses import dataclass
import json
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404

from ad_main.typed_settings import get_technical_reports_root


@dataclass(frozen=True, slots=True)
class TechnicalReport:
    """Metadata for a technical report PDF."""

    key: str
    filename: str
    output_filename: str
    title: str | None = None
    published: bool = False
    order: Any = None


def load_technical_reports_manifest() -> dict[str, TechnicalReport]:
    """Load technical report metadata from a JSON manifest.

    The manifest is expected to be located at:
    Path(settings.TECHNICAL_REPORTS_ROOT) / "technical_reports.json"
    """
    root = get_technical_reports_root()
    manifest_path = root / "technical_reports.json"

    if not manifest_path.exists():
        raise ImproperlyConfigured(
            f"Technical reports manifest not found at {manifest_path}"
        )

    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ImproperlyConfigured(
            f"Invalid JSON in technical reports manifest: {e}"
        )

    if not isinstance(data, dict):
        raise ImproperlyConfigured(
            "Technical reports manifest must be a JSON object."
        )

    # Determine report entries and default reference
    if "reports" in data and isinstance(data["reports"], dict):
        entries = data["reports"]
        default_ref = data.get("default")
    else:
        entries = data
        default_ref = data.get("default")

    reports: dict[str, TechnicalReport] = {}
    for key, entry in entries.items():
        if key == "default" and not isinstance(entry, dict):
            continue
        if not isinstance(entry, dict):
            raise ImproperlyConfigured(
                f"Entry for report '{key}' must be an object."
            )

        filename = entry.get("filename")
        output_filename = entry.get("output_filename")
        title = entry.get("title")
        published = bool(entry.get("published", False))
        order = entry.get("order")

        if (
            not filename
            or not isinstance(filename, str)
            or not filename.strip()
        ):
            raise ImproperlyConfigured(
                f"Report '{key}' must have a non-empty string 'filename'."
            )
        if (
            not output_filename
            or not isinstance(output_filename, str)
            or not output_filename.strip()
        ):
            raise ImproperlyConfigured(
                f"Report '{key}' must have a non-empty string 'output_filename'."
            )

        reports[key] = TechnicalReport(
            key=key,
            filename=filename,
            output_filename=output_filename,
            title=title,
            published=published,
            order=order,
        )

    # Resolve "default" if defined as a string reference
    if isinstance(default_ref, str):
        if default_ref not in reports:
            raise ImproperlyConfigured(
                f"Default report '{default_ref}' not found in manifest."
            )
        ref_report = reports[default_ref]
        reports["default"] = TechnicalReport(
            key="default",
            filename=ref_report.filename,
            output_filename=ref_report.output_filename,
            title=ref_report.title,
            published=ref_report.published,
            order=ref_report.order,
        )
    elif "default" not in reports and default_ref is not None:
        if not isinstance(default_ref, dict):
            raise ImproperlyConfigured(
                "Entry for report 'default' must be an object or a key string."
            )

    return reports


def get_published_technical_reports() -> list[TechnicalReport]:
    """Retrieve published technical reports ordered for display."""
    try:
        reports = load_technical_reports_manifest()
    except ImproperlyConfigured:
        return []

    published = [
        report
        for key, report in reports.items()
        if key != "default" and report.published
    ]

    def _sort_key(report: TechnicalReport):
        if report.order is None:
            return (1, 0, report.key)
        if isinstance(report.order, (int, float)):
            return (0, report.order, report.key)
        return (0, str(report.order), report.key)

    published.sort(key=_sort_key)
    return published


def serve_technical_report_pdf(
    _request,
    report_key="default",
    *_args,
    **_kwargs,
):
    """Service to serve technical report PDFs from a manifest."""
    if report_key is None:
        report_key = "default"

    try:
        reports = load_technical_reports_manifest()
    except ImproperlyConfigured as e:
        # Configuration errors should fail loudly (500)
        raise e

    report = reports.get(report_key)
    if report is None:
        raise Http404("Technical Report PDF not found")

    root = get_technical_reports_root().resolve()

    # Resolve path and check for traversal
    try:
        pdf_path = (root / report.filename).resolve()
        # Ensure the resolved path is within the root directory
        pdf_path.relative_to(root)
    except (ValueError, RuntimeError):
        # Path is outside root or cannot be resolved relative to it
        raise Http404("Technical Report PDF not found")

    if not pdf_path.exists() or not pdf_path.is_file():
        raise Http404("Technical Report PDF not found")

    if pdf_path.suffix.lower() != ".pdf":
        raise Http404("Technical Report PDF not found")

    # Use FileResponse for streaming large files
    response = FileResponse(
        pdf_path.open("rb"), content_type="application/pdf"
    )
    response["Content-Disposition"] = (
        f'inline; filename="{report.output_filename}"'
    )

    return response
