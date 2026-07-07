import json
from pathlib import Path
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import reverse


def _download_view() -> Any:
    from dados.technical_reports import serve_technical_report_pdf

    return serve_technical_report_pdf


def _consume_response(response: Any) -> bytes:
    content = b"".join(response.streaming_content)
    response.close()
    return content


def test_download_technical_report_pdf_success(
    tmp_path: Path,
) -> None:
    # Setup manifest and PDF
    manifest = {
        "default": {
            "filename": "report.pdf",
            "output_filename": "Output Report.pdf",
        }
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    pdf_content = b"%PDF-1.4 technical report"
    (tmp_path / "report.pdf").write_bytes(pdf_content)

    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        response = download_technical_report_pdf(RequestFactory().get("/"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith("inline;")
    assert "Output Report.pdf" in response["Content-Disposition"]
    assert _consume_response(response) == pdf_content


def test_download_technical_report_pdf_unknown_key(
    tmp_path: Path,
) -> None:
    manifest = {"default": {"filename": "a.pdf", "output_filename": "b.pdf"}}
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(Http404, match="Technical Report PDF not found"):
            download_technical_report_pdf(
                RequestFactory().get("/"), report_key="unknown"
            )


def test_download_technical_report_pdf_missing_file(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": {"filename": "missing.pdf", "output_filename": "b.pdf"}
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(Http404, match="Technical Report PDF not found"):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_download_technical_report_pdf_path_traversal(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": {"filename": "../secret.pdf", "output_filename": "b.pdf"}
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path.parent / "secret.pdf").write_bytes(b"secret")

    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(Http404, match="Technical Report PDF not found"):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_download_technical_report_pdf_non_pdf(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": {"filename": "report.txt", "output_filename": "b.pdf"}
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "report.txt").write_text("not a pdf")

    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(Http404, match="Technical Report PDF not found"):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_manifest_missing_raises_improperly_configured(
    tmp_path: Path,
) -> None:
    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(ImproperlyConfigured, match="manifest not found"):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_manifest_invalid_json_raises_improperly_configured(
    tmp_path: Path,
) -> None:
    (tmp_path / "technical_reports.json").write_text(
        "invalid json", encoding="utf-8"
    )
    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(ImproperlyConfigured, match="Invalid JSON"):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_manifest_invalid_structure_raises_improperly_configured(
    tmp_path: Path,
) -> None:
    # Root not a dict
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(["not a dict"]), encoding="utf-8"
    )
    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(
            ImproperlyConfigured, match="must be a JSON object"
        ):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_manifest_invalid_entry_raises_improperly_configured(
    tmp_path: Path,
) -> None:
    # Entry missing filename
    manifest = {"default": {"output_filename": "b.pdf"}}
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(
            ImproperlyConfigured,
            match="must have a non-empty string 'filename'",
        ):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_home_technical_report_link_uses_download_route() -> None:
    content = render_to_string(
        "components/home/home_functionalities_section.html"
    )

    assert (
        f'href="{reverse("dados:download_technical_report_pdf")}"' in content
    )


def test_services_api_download_button_shows_selected_format() -> None:
    content = (
        Path(__file__).resolve().parents[2]
        / "dados/templates/services_api.html"
    ).read_text()

    assert (
        'label for="format">' in content
        and '{% translate "Selecione o formato do arquivo de saída" %}'
        in content
    )
    assert 'id="download-button"' in content
    assert 'id="download-format-label">CSV</span>' in content
    assert "fa fa-download" in content
