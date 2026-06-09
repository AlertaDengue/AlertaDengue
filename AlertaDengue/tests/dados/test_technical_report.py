from pathlib import Path
from typing import Any

import pytest
from django.http import Http404
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import reverse


def _download_view(monkeypatch: pytest.MonkeyPatch) -> Any:
    import locale

    monkeypatch.setattr(locale, "setlocale", lambda *args, **kwargs: None)
    from dados.views import download_technical_report_pdf

    return download_technical_report_pdf


def test_download_technical_report_pdf_uses_configured_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_content = b"%PDF-1.4 technical report"
    (tmp_path / "technical-report.pdf").write_bytes(pdf_content)
    download_technical_report_pdf = _download_view(monkeypatch)

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        response = download_technical_report_pdf(RequestFactory().get("/"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith("inline;")
    assert response.content == pdf_content


def test_download_technical_report_pdf_returns_404_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_technical_report_pdf = _download_view(monkeypatch)

    with override_settings(TECHNICAL_REPORTS_ROOT=tmp_path):
        with pytest.raises(Http404, match="Technical Report PDF not found"):
            download_technical_report_pdf(RequestFactory().get("/"))


def test_home_technical_report_link_uses_download_route() -> None:
    content = render_to_string(
        "components/home/home_functionalities_section.html"
    )

    assert (
        f'href="{reverse("dados:download_technical_report_pdf")}"' in content
    )
