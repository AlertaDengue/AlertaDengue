"""Tests for city-report view helpers."""

from __future__ import annotations

from decimal import Decimal
import logging
from pathlib import Path
from typing import Any

from django.utils.translation import gettext, override
import pandas as pd
import plotly.graph_objs as go
import pytest

from dados.charts.cities import ReportCityCharts
from dados.dbdata import ReportParameters
from dados.views import get_report_table_html, get_var_params


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

    assert (
        "°C temperatura mínima" in html
        or r"\u00b0C temperatura m\u00ednima" in html
    )
    assert "temp.min" not in html
    assert (
        "Limiar favorável 18°C" in html
        or r"Limiar favor\u00e1vel 18\u00b0C" in html
    )
    assert '"responsive": true' in html
    assert "height:520px" in html
    assert "width:100%" in html
    assert '"width": 1100' not in html


def test_create_climate_chart_returns_empty_without_variables() -> None:
    df = pd.DataFrame({"SE": [202501]})

    assert ReportCityCharts.create_climate_chart(df=df, var_climate={}) == ""


def test_create_incidence_chart_renders_thresholds_above_alert_bars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, go.Figure] = {}

    def capture_figure(figure: go.Figure, *args: Any, **kwargs: Any) -> str:
        captured["figure"] = figure
        return ""

    monkeypatch.setattr(go.Figure, "to_html", capture_figure)

    df = pd.DataFrame(
        {
            "incidência": [10.0, 20.0],
            "casos notif.": [1, 2],
            "casos_est": [1.5, 2.5],
            "level_code": [1, 3],
        },
        index=pd.Index([202501, 202502], name="SE"),
    )

    ReportCityCharts.create_incidence_chart(
        df=df,
        year_week=202502,
        threshold_pre_epidemic=5,
        threshold_pos_epidemic=10,
        threshold_epidemic=15,
    )
    figure = captured["figure"]

    assert [trace.name for trace in figure.data] == [
        "Notificações (casos)",
        "Estimados (Nowcast, casos)",
        "Alerta Verde",
        "Alerta Amarelo",
        "Alerta Laranja",
        "Alerta Vermelho",
        "Limiar Pré Epidêmico",
        "Limiar Pós Epidêmico",
        "Limiar Epidêmico",
    ]
    assert [trace.legendrank for trace in figure.data] == [
        0,
        1,
        5,
        6,
        7,
        8,
        2,
        3,
        4,
    ]

    threshold_traces = figure.data[-3:]
    assert all(trace.type == "scatter" for trace in threshold_traces)
    assert all(trace.mode == "lines" for trace in threshold_traces)
    assert all(trace.line.width == 3 for trace in threshold_traces)
    assert all(trace.line.dash == "dash" for trace in threshold_traces)
    assert all(list(trace.x) == [None] for trace in threshold_traces)
    assert all(list(trace.y) == [None] for trace in threshold_traces)

    threshold_shapes = figure.layout.shapes
    assert len(threshold_shapes) == 3
    assert all(shape.type == "line" for shape in threshold_shapes)
    assert all(shape.layer == "above" for shape in threshold_shapes)
    assert all(shape.yref == "y" for shape in threshold_shapes)
    assert all(shape.xref == "x domain" for shape in threshold_shapes)
    assert [shape.x0 for shape in threshold_shapes] == [0, 0, 0]
    assert [shape.x1 for shape in threshold_shapes] == [1, 1, 1]
    assert [shape.y0 for shape in threshold_shapes] == [5, 10, 15]
    assert [shape.y1 for shape in threshold_shapes] == [5, 10, 15]
    assert [shape.line.color for shape in threshold_shapes] == [
        "rgb(0,128,0)",
        "rgb(204,102,0)",
        "rgb(255,0,0)",
    ]
    assert all(shape.line.width == 3 for shape in threshold_shapes)
    assert all(shape.line.dash == "dash" for shape in threshold_shapes)

    nowcast_trace = figure.data[1]
    assert nowcast_trace.line.width == 4
    assert nowcast_trace.line.dash == "dot"
    assert nowcast_trace.line.color == "#4169e1"
    assert figure.layout.xaxis.gridcolor == "rgba(176, 196, 222, 0.45)"
    assert figure.layout.yaxis.gridcolor == "rgba(176, 196, 222, 0.45)"
    assert figure.layout.yaxis.rangemode == "tozero"
    assert figure.layout.yaxis2.rangemode == "tozero"
    assert [trace.line.color for trace in threshold_traces] == [
        "rgb(0,128,0)",
        "rgb(204,102,0)",
        "rgb(255,0,0)",
    ]
    assert [trace.marker.color for trace in figure.data[2:6]] == [
        "rgb(0,255,0)",
        "rgb(255,255,0)",
        "rgb(255,150,0)",
        "rgb(255,0,0)",
    ]


def test_incidence_chart_labels_translate_in_spanish_and_english() -> None:
    with override("es"):
        assert gettext("pós epidêmico") == "post epidémico"
        assert gettext("Notificações (casos)") == "Notificaciones (casos)"
        assert (
            gettext("Estimados (Nowcast, casos)")
            == "Estimados (Nowcast, casos)"
        )

    with override("en"):
        assert gettext("Notificações (casos)") == "Notifications (cases)"
        assert (
            gettext("Estimados (Nowcast, casos)")
            == "Estimated (Nowcast, cases)"
        )


def test_report_city_template_uses_translated_alert_level_mapping() -> None:
    html = (
        Path(__file__).resolve().parents[2]
        / "dados/templates/report_city.html"
    ).read_text()

    assert "'{% translate \"verde\" %}': 'green-row'" in html
    assert "'{% translate \"amarelo\" %}': 'yellow-row'" in html
    assert "function normalizeLevel(value)" not in html
    assert ".table-striped tbody tr.yellow-row > td" in html
    assert '<div class="plotly-chart w-100">' in html
    assert ".plotly-chart .plotly-graph-div" in html
