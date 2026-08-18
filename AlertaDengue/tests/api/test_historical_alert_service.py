from datetime import date
from unittest.mock import MagicMock

import pytest

from api.internal.historical_alerts import (
    DEFAULT_HISTORICAL_ALERT_LIMIT,
    HistoricalAlertFilters,
    build_historical_alert_queryset,
    get_historical_alert_queryset,
    get_historical_alert_response_fields,
    serialize_historical_alert,
)
from dados import dbdata
from dados.models import (
    LegacyHistoricalAlertChikungunya,
    LegacyHistoricalAlertDengue,
    LegacyHistoricalAlertZika,
)
from dados.services import historical_alerts
from dados.services.historical_alerts import (
    get_latest_historical_alert_week,
    get_legacy_historical_alert_model,
)


@pytest.mark.parametrize(
    ("disease", "model"),
    [
        ("dengue", LegacyHistoricalAlertDengue),
        ("chik", LegacyHistoricalAlertChikungunya),
        ("chikungunya", LegacyHistoricalAlertChikungunya),
        ("zika", LegacyHistoricalAlertZika),
    ],
)
def test_historical_alert_disease_routing(disease, model):
    assert get_legacy_historical_alert_model(disease) is model
    queryset = build_historical_alert_queryset(HistoricalAlertFilters(disease))
    assert queryset.model is model


def test_historical_alert_service_rejects_unknown_disease():
    with pytest.raises(ValueError, match="supported values"):
        HistoricalAlertFilters("yellow-fever")


def test_latest_historical_alert_week_uses_normalized_orm_fields(monkeypatch):
    values = MagicMock()
    values.first.return_value = 202601
    queryset = MagicMock()
    queryset.values_list.return_value = values
    model = MagicMock()
    model.objects.order_by.return_value = queryset
    monkeypatch.setattr(
        historical_alerts,
        "get_legacy_historical_alert_model",
        lambda disease: model,
    )

    assert get_latest_historical_alert_week("chik") == 202601
    model.objects.order_by.assert_called_once_with(
        "-epidemiological_week_start_date"
    )
    queryset.values_list.assert_called_once_with(
        "epidemiological_week", flat=True
    )
    values.first.assert_called_once_with()


def test_get_last_se_delegates_to_the_historical_alert_service(monkeypatch):
    service = MagicMock(return_value=202601)
    monkeypatch.setattr(dbdata, "get_latest_historical_alert_week", service)

    assert dbdata.get_last_SE("zika").cdcformat() == "202601"
    service.assert_called_once_with("zika")


def test_historical_alert_queryset_uses_normalized_filters_and_table():
    queryset = get_historical_alert_queryset(
        "dengue",
        municipality_geocode=3304557,
        epidemiological_week=202601,
    )

    sql = str(queryset.query)

    assert queryset.model is LegacyHistoricalAlertDengue
    assert '"Municipio"."Historico_alerta"' in sql
    assert '"municipio_geocodigo"' in sql
    assert '"SE"' in sql
    assert f"LIMIT {DEFAULT_HISTORICAL_ALERT_LIMIT}" in sql


def test_historical_alert_range_filters_and_ordering_are_applied():
    queryset = get_historical_alert_queryset(
        "zika",
        start_week=202601,
        end_week=202652,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        ordering="epidemiological_week",
    )
    sql = str(queryset.query)

    assert queryset.model is LegacyHistoricalAlertZika
    assert '"SE" >=' in sql
    assert '"SE" <=' in sql
    assert '"data_iniSE" >=' in sql
    assert '"data_iniSE" <=' in sql
    assert '"SE" ASC' in sql


@pytest.mark.parametrize(
    "filters",
    [
        {"start_week": 202652, "end_week": 202601},
        {"start_date": date(2026, 2, 1), "end_date": date(2026, 1, 1)},
        {"limit": -1},
        {"limit": 5001},
        {"offset": -1},
        {"ordering": "municipality_geocode; DROP TABLE alerts"},
    ],
)
def test_historical_alert_service_rejects_unsafe_filters(filters):
    with pytest.raises(ValueError):
        HistoricalAlertFilters("dengue", **filters)


def test_historical_alert_serialization_uses_normalized_response_fields():
    record = LegacyHistoricalAlertDengue(
        municipality_geocode=3304557,
        municipality_name="Rio de Janeiro",
        epidemiological_week=202601,
        epidemiological_week_start_date=date(2026, 1, 4),
        estimated_cases=12.5,
        probable_cases=11,
    )

    serialized = serialize_historical_alert(record, "chik")

    assert serialized["disease"] == "chikungunya"
    assert serialized["epidemiological_week_start_date"] == "2026-01-04"
    assert set(serialized) == set(get_historical_alert_response_fields())
    for legacy_key in (
        "SE",
        "data_iniSE",
        "Localidade_id",
        "municipio_geocodigo",
        "casos_est",
        "p_rt1",
        "p_inc100k",
    ):
        assert legacy_key not in serialized
