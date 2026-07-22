"""Regression tests for the retained legacy state-dashboard query flow."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, call, patch

from django.test import RequestFactory
from django.urls import resolve, reverse
import pandas as pd
import pytest
from sqlalchemy.sql.elements import BindParameter

from api.views import NotificationReducedCSV_View
from dados.dbdata import get_estimated_cases_by_cities
from dados.views import (
    AlertaStateView,
    ChartsMainView,
    _count_municipalities,
)


@pytest.mark.parametrize(
    ("geocodes", "expected"),
    [
        ([3304557, 3304557], 1),
        ([3304557, 3550308], 2),
        ([3304557, None, float("nan")], 1),
        ([], 0),
    ],
)
def test_count_municipalities_uses_distinct_non_null_geocodes(
    geocodes: list[object], expected: int
) -> None:
    frame = pd.DataFrame({"municipio_geocodigo": geocodes})

    count = _count_municipalities(frame)

    assert count == expected
    assert isinstance(count, int)


def test_count_municipalities_accepts_empty_state_history() -> None:
    assert _count_municipalities(pd.DataFrame()) == 0


@patch("dados.views._create_stack_chart", return_value="stack")
@patch("dados.views.data_hist_uf")
@patch.object(ChartsMainView, "get_img_map", return_value="map")
def test_charts_main_view_preserves_count_cities_context(
    _get_img_map: MagicMock,
    data_hist_uf: MagicMock,
    _create_stack_chart: MagicMock,
) -> None:
    def state_history(geocodes: list[int | None]) -> pd.DataFrame:
        row_count = len(geocodes)
        return pd.DataFrame(
            {
                "SE": [202502] * row_count,
                "casos_est": [0] * row_count,
                "casos": [0] * row_count,
                "nivel": [1] * row_count,
                "municipio_geocodigo": geocodes,
            }
        )

    data_hist_uf.side_effect = [
        state_history([3304557, 3304557, 3550308, None]),
        state_history([3304557]),
        state_history([3304557, 3550308, 4106902]),
    ]

    context = ChartsMainView().get_context_data(state="RJ")

    assert context["count_cities"] == {
        "dengue": {"RJ": 2},
        "chikungunya": {"RJ": 1},
        "zika": {"RJ": 3},
    }
    assert data_hist_uf.call_args_list == [
        call(state_abbv="RJ", disease="dengue"),
        call(state_abbv="RJ", disease="chikungunya"),
        call(state_abbv="RJ", disease="zika"),
    ]


def _query_engine() -> MagicMock:
    engine = MagicMock()
    result = (
        engine.connect.return_value.__enter__.return_value.execute.return_value
    )
    result.fetchall.return_value = [(3304557, date(2025, 1, 5), 12.5)]
    result.keys.return_value = [
        "municipio_geocodigo",
        "data_iniSE",
        "casos_est",
    ]
    return engine


@pytest.mark.parametrize(
    ("disease", "table_name"),
    [
        ("dengue", "Historico_alerta"),
        ("chikungunya", "Historico_alerta_chik"),
        ("zika", "Historico_alerta_zika"),
    ],
)
def test_estimated_cases_select_only_the_disease_table(
    disease: str, table_name: str
) -> None:
    engine = _query_engine()

    frame = get_estimated_cases_by_cities(
        [3304557], disease=disease, db_engine=engine
    )

    statement, params = (
        engine.connect.return_value.__enter__.return_value.execute.call_args.args
    )
    sql = str(statement)
    assert f'"Municipio"."{table_name}"' in sql
    for other_table in {
        "Historico_alerta",
        "Historico_alerta_chik",
        "Historico_alerta_zika",
    } - {table_name}:
        assert f'"Municipio"."{other_table}"' not in sql
    assert params == {"geo_ids": [3304557], "n": 12}
    assert frame["casos_est"].tolist() == [12.5]
    assert list(frame.columns) == [
        "municipio_geocodigo",
        "data_iniSE",
        "casos_est",
    ]
    assert pd.api.types.is_datetime64_any_dtype(frame["data_iniSE"])


def test_estimated_cases_select_last_n_rows_per_municipality() -> None:
    engine = _query_engine()

    get_estimated_cases_by_cities(
        [3304557, 3550308], disease="dengue", n=4, db_engine=engine
    )

    statement, params = (
        engine.connect.return_value.__enter__.return_value.execute.call_args.args
    )
    sql = str(statement)
    assert "PARTITION BY municipio_geocodigo" in sql
    assert 'ORDER BY "data_iniSE" DESC' in sql
    assert "WHERE rn <= :n" in sql
    assert 'ORDER BY municipio_geocodigo, "data_iniSE"' in sql
    assert params == {"geo_ids": [3304557, 3550308], "n": 4}
    geo_ids_parameter = statement._bindparams["geo_ids"]
    assert isinstance(geo_ids_parameter, BindParameter)
    assert geo_ids_parameter.expanding is True
    n_parameter = statement._bindparams["n"]
    assert isinstance(n_parameter, BindParameter)
    assert n_parameter.expanding is False


def test_estimated_cases_empty_geocodes_do_not_query_database() -> None:
    engine = MagicMock()

    frame = get_estimated_cases_by_cities([], "dengue", db_engine=engine)

    assert frame.empty
    assert list(frame.columns) == [
        "municipio_geocodigo",
        "data_iniSE",
        "casos_est",
    ]
    engine.connect.assert_not_called()


def test_estimated_cases_reject_invalid_disease() -> None:
    with pytest.raises(ValueError, match="Unsupported disease"):
        get_estimated_cases_by_cities([], "influenza")


@patch("dados.views.get_last_SE")
@patch("dados.views.get_estimated_cases_by_cities")
@patch("dados.views.get_cities_alert_by_state")
def test_alerta_state_view_uses_route_disease_for_case_series(
    get_cities_alert_by_state: MagicMock,
    get_estimated_cases_by_cities: MagicMock,
    get_last_se: MagicMock,
) -> None:
    get_cities_alert_by_state.return_value = pd.DataFrame(
        {
            "municipio_geocodigo": [3304557, 3550308],
            "nome": ["Rio de Janeiro", "São Paulo"],
            "level_alert": [1, 2],
        }
    )
    get_estimated_cases_by_cities.return_value = pd.DataFrame(
        {
            "municipio_geocodigo": [3550308, 3304557, 3304557],
            "data_iniSE": pd.to_datetime(
                ["2025-01-12", "2025-01-12", "2025-01-05"]
            ),
            "casos_est": [20.0, 12.0, 10.0],
        }
    )
    get_last_se.return_value.enddate.return_value = date(2025, 1, 12)

    view = AlertaStateView()
    context = view.get_context_data(state="RJ", disease="zika")

    assert view.template_name == "state_cities.html"
    get_cities_alert_by_state.assert_called_once_with("Rio de Janeiro", "zika")
    get_estimated_cases_by_cities.assert_called_once_with(
        geo_ids=[3304557, 3550308],
        disease="zika",
        n=12,
    )
    assert context["case_series"] == {
        3304557: [10.0, 12.0],
        3550308: [20.0],
    }
    assert context["disease_label"] == "Zika"


def test_legacy_state_dashboard_route_remains_available() -> None:
    path = reverse(
        "dados:alerta_uf", kwargs={"state": "RJ", "disease": "zika"}
    )
    match = resolve(path)

    assert path == "/alerta/RJ/zika"
    assert match.url_name == "alerta_uf"
    assert match.func.view_class is AlertaStateView


@patch("api.views.NotificationQueries")
def test_reduced_notification_api_contract(
    notification_queries: MagicMock,
) -> None:
    notification_queries.return_value.get_disease_dist.return_value = (
        pd.DataFrame(
            {"casos": [3]}, index=pd.Index(["Dengue"], name="category")
        )
    )
    request = RequestFactory().get(
        "/api/notif_reduced",
        {"state_abv": "RJ", "chart_type": "disease"},
    )
    path = reverse("api:notif_reduced")
    match = resolve(path)

    response = NotificationReducedCSV_View.as_view()(request)

    assert path == "/api/notif_reduced"
    assert match.func.view_class is NotificationReducedCSV_View
    assert response.status_code == 200
    assert b"category,casos" in response.content
    assert b"Dengue,3" in response.content
    notification_queries.assert_called_once()
