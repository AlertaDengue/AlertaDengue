from dataclasses import dataclass
import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404


@dataclass(frozen=True, slots=True)
class TechnicalReport:
    """Metadata for a technical report PDF."""

    key: str
    filename: str
    output_filename: str


def load_technical_reports_manifest() -> dict[str, TechnicalReport]:
    """Load technical report metadata from a JSON manifest.

    The manifest is expected to be located at:
    Path(settings.TECHNICAL_REPORTS_ROOT) / "technical_reports.json"
    """
    root = Path(settings.TECHNICAL_REPORTS_ROOT)
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

    reports = {}
    for key, entry in data.items():
        if not isinstance(entry, dict):
            raise ImproperlyConfigured(
                f"Entry for report '{key}' must be an object."
            )

        filename = entry.get("filename")
        output_filename = entry.get("output_filename")

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
            key=key, filename=filename, output_filename=output_filename
        )

    return reports


def serve_technical_report_pdf(
    _request,
    report_key="default",
    *_args,
    **_kwargs,
):
    """Service to serve technical report PDFs from a manifest."""
    try:
        reports = load_technical_reports_manifest()
    except ImproperlyConfigured as e:
        # Configuration errors should fail loudly (500)
        raise e

    report = reports.get(report_key)
    if report is None:
        raise Http404("Technical Report PDF not found")

    root = Path(settings.TECHNICAL_REPORTS_ROOT).resolve()

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
