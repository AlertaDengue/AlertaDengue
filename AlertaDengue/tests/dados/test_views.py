"""Tests for city-report view helpers."""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from dados.charts.cities import ReportCityCharts
from dados.dbdata import ReportParameters
from dados.views import get_report_table_html, get_var_params
from django.utils.translation import override


def make_parameters(
    varcli: Any = None,
    clicrit: Any = None,
    varcli2: Any = None,
    clicrit2: Any = None,
) -> ReportParameters:
    """Build report parameters using the production result type."""
    return ReportParameters(
        cid10="A90",
        municipio_geocodigo=3304557,
        varcli=varcli,
        clicrit=clicrit,
        varcli2=varcli2,
        clicrit2=clicrit2,
        limiar_preseason=100,
        limiar_posseason=80,
        limiar_epidemico=300,
    )


def test_get_var_params_returns_empty_for_missing_parameters() -> None:
    assert get_var_params(None) == ({}, [])


def test_get_var_params_normalizes_valid_keys() -> None:
    parameters = make_parameters("temp_min", 22, "umid_med", 60)

    variables, keys = get_var_params(parameters)

    assert keys == ["temp.min", "umid.med"]
    assert variables["temp.min"][1] == 22
    assert variables["umid.med"][1] == 60


@pytest.mark.parametrize("invalid_key", [None, "", float("nan"), "NA"])
def test_get_var_params_skips_invalid_keys(invalid_key: Any) -> None:
    parameters = make_parameters(invalid_key, 10, "temp_max", 30)

    variables, keys = get_var_params(parameters)

    assert keys == ["temp.max"]
    assert list(variables) == ["temp.max"]


def test_get_var_params_logs_unknown_keys(
    caplog: pytest.LogCaptureFixture,
) -> None:
    parameters = make_parameters("unknown_var", 10)

    with caplog.at_level(logging.WARNING, logger="dados.views"):
        variables, keys = get_var_params(parameters)

    assert variables == {}
    assert keys == []
    assert "Skipping invalid varclimate key 'unknown_var'" in caplog.text


def test_report_parameters_are_immutable() -> None:
    parameters = make_parameters("temp_min", 22)

    with pytest.raises(AttributeError):
        parameters.varcli = "temp_max"


def test_get_report_table_html_formats_climate_values() -> None:
    df = pd.DataFrame(
        {
            "SE": [202501],
            "temp.min": [Decimal("20.1318714285714")],
            "casos notif.": [Decimal("12")],
            "casos_est": [Decimal("18")],
            "incidência": [Decimal("44.44")],
            "nivel": ["verde"],
        }
    ).set_index("SE")

    html = get_report_table_html(df, ["temp.min"])

    assert "20.1" in html
    assert "20.1318714285714" not in html
    assert ">12<" in html
    assert ">44.4<" in html
    assert ">verde<" in html


def test_get_report_table_html_translates_alert_level() -> None:
    df = pd.DataFrame(
        {
            "SE": [202501],
            "temp.min": [Decimal("20.1")],
            "casos notif.": [Decimal("12")],
            "casos_est": [Decimal("18")],
            "incidência": [Decimal("44.4")],
            "nivel": ["amarelo"],
        }
    ).set_index("SE")

    with override("en"):
        html = get_report_table_html(df, ["temp.min"])

    assert ">Yellow<" in html
    assert ">amarelo<" not in html


def test_create_climate_chart_coerces_numeric_series() -> None:
    df = pd.DataFrame(
        {
            "SE": [202501, 202502],
            "temp.min": [Decimal("20.1"), Decimal("21.2")],
        }
    )

    html = ReportCityCharts.create_climate_chart(
        df=df,
        var_climate={"temp.min": ["°C temperatura mínima", 18]},
    )

    assert "°C temperatura mínima" in html
    assert "temp.min" not in html
    assert "Limiar favorável" in html


def test_create_climate_chart_returns_empty_without_variables() -> None:
    df = pd.DataFrame({"SE": [202501]})

    assert ReportCityCharts.create_climate_chart(df=df, var_climate={}) == ""


def test_report_city_template_uses_translated_alert_level_mapping() -> None:
    html = Path("AlertaDengue/dados/templates/report_city.html").read_text()

    assert "'{% translate \"verde\" %}': 'green-row'" in html
    assert "'{% translate \"amarelo\" %}': 'yellow-row'" in html
    assert "function normalizeLevel(value)" not in html
    assert ".table-striped tbody tr.yellow-row > td" in html
