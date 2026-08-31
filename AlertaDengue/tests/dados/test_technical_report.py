import json
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import reverse
import pytest


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


def test_download_technical_report_pdf_wrapper_passes_selected_key(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": {
            "filename": "default.pdf",
            "output_filename": "Default.pdf",
        },
        "technical-report-2023": {
            "filename": "selected.pdf",
            "output_filename": "Selected.pdf",
        },
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "default.pdf").write_bytes(b"%PDF-1.4 default")
    selected_pdf = b"%PDF-1.4 selected"
    (tmp_path / "selected.pdf").write_bytes(selected_pdf)

    from dados.views import download_technical_report_pdf

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        response = download_technical_report_pdf(
            RequestFactory().get("/"), report_key="technical-report-2023"
        )

    assert response.status_code == 200
    assert "Selected.pdf" in response["Content-Disposition"]
    assert _consume_response(response) == selected_pdf


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
        f'href="{reverse("dados:download_technical_report_pdf", kwargs={"report_key": "technical-report-2023"})}"'
        in content
    )


def test_home_banner_technical_report_link_uses_default_endpoint() -> None:
    content = render_to_string("components/home/home_banners_section.html")

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


def test_products_technical_report_links_rendered_from_manifest(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": "report-01",
        "reports": {
            "report-01": {
                "filename": "report-01.pdf",
                "output_filename": "Report 01.pdf",
                "title": "Relatório Técnico Especial 01",
                "published": True,
                "order": 1,
            },
            "report-02": {
                "filename": "report-02.pdf",
                "output_filename": "Report 02.pdf",
                "title": "Relatório Técnico Especial 02",
                "published": True,
                "order": 2,
            },
            "draft-report": {
                "filename": "draft.pdf",
                "output_filename": "Draft.pdf",
                "title": "Relatório Técnico em Rascunho",
                "published": False,
                "order": 3,
            },
        },
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "report-01.pdf").write_bytes(b"%PDF-1.4 report 1")
    (tmp_path / "report-02.pdf").write_bytes(b"%PDF-1.4 report 2")
    (tmp_path / "draft.pdf").write_bytes(b"%PDF-1.4 draft")

    from dados.technical_reports import get_published_technical_reports

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        published_reports = get_published_technical_reports()
        assert len(published_reports) == 2
        assert [r.key for r in published_reports] == ["report-01", "report-02"]

        content = render_to_string(
            "products.html", {"technical_reports": published_reports}
        )

        for report in published_reports:
            url = reverse(
                "dados:download_technical_report_pdf",
                kwargs={"report_key": report.key},
            )
            assert f'href="{url}"' in content
            assert report.title in content

        assert "Relatório Técnico em Rascunho" not in content


def test_products_page_view_context_includes_published_reports(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": "report-01",
        "reports": {
            "report-01": {
                "filename": "report-01.pdf",
                "output_filename": "Report 01.pdf",
                "title": "Relatório Técnico Publicado",
                "published": True,
                "order": 1,
            },
            "draft-01": {
                "filename": "draft.pdf",
                "output_filename": "Draft.pdf",
                "title": "Relatório Não Publicado",
                "published": False,
            },
        },
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "report-01.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "draft.pdf").write_bytes(b"%PDF-1.4")

    from dados.views import ProductsPageView

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        view = ProductsPageView()
        view.setup(RequestFactory().get("/produtos/"))
        context = view.get_context_data()

        assert "technical_reports" in context
        assert len(context["technical_reports"]) == 1
        assert context["technical_reports"][0].key == "report-01"
        assert (
            context["technical_reports"][0].title
            == "Relatório Técnico Publicado"
        )


def test_manifest_string_default_reference_serves_target_pdf(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": "epidemiological-situation-analysis-2026-03",
        "reports": {
            "epidemiological-situation-analysis-2026-03": {
                "filename": "analysis-03.pdf",
                "output_filename": "RELATÓRIO TÉCNICO 03.pdf",
                "title": "Análise 03",
                "published": True,
            }
        },
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    pdf_content = b"%PDF-1.4 content for 03"
    (tmp_path / "analysis-03.pdf").write_bytes(pdf_content)

    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        response = download_technical_report_pdf(RequestFactory().get("/"))

    assert response.status_code == 200
    assert "RELATÓRIO TÉCNICO 03.pdf" in response["Content-Disposition"]
    assert _consume_response(response) == pdf_content


def test_manifest_invalid_default_reference_raises_improperly_configured(
    tmp_path: Path,
) -> None:
    manifest = {
        "default": "non-existent-key",
        "reports": {
            "report-01": {
                "filename": "report-01.pdf",
                "output_filename": "Report 01.pdf",
            }
        },
    }
    (tmp_path / "technical_reports.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    download_technical_report_pdf = _download_view()

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(
            ImproperlyConfigured,
            match="Default report 'non-existent-key' not found",
        ):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_get_published_technical_reports_handles_missing_manifest(
    tmp_path: Path,
) -> None:
    from dados.technical_reports import get_published_technical_reports

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        assert get_published_technical_reports() == []
