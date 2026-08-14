from datetime import date
from unittest.mock import MagicMock

from django.db.models import QuerySet
from django.urls import reverse
import pytest
from rest_framework.test import APIClient

from api.internal import views
from dados.models import LegacyHistoricalAlertDengue


@pytest.fixture()
def api_client():
    """Return the current REST API test client."""
    return APIClient()


@pytest.fixture()
def internal_api_client(api_client):
    """Return a client allowed by the existing internal group permission."""
    user = MagicMock()
    user.is_authenticated = True
    user.is_active = True
    user.is_superuser = False
    user.groups.filter.return_value.exists.return_value = True
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture()
def historical_alert_record():
    """Return an unsaved historical alert for serialization tests."""
    return LegacyHistoricalAlertDengue(
        municipality_geocode=3304557,
        municipality_name="Rio de Janeiro",
        epidemiological_week=202601,
        epidemiological_week_start_date=date(2026, 1, 4),
        estimated_cases=12.5,
        probable_cases=11,
    )


@pytest.fixture()
def bounded_queryset(monkeypatch, historical_alert_record):
    """Keep endpoint tests at the bounded QuerySet evaluation boundary."""
    monkeypatch.setattr(
        QuerySet,
        "__iter__",
        lambda _queryset: iter([historical_alert_record]),
    )


@pytest.mark.parametrize(
    ("disease", "expected_disease"),
    [
        ("dengue", "dengue"),
        ("chik", "chikungunya"),
        ("chikungunya", "chikungunya"),
        ("zika", "zika"),
    ],
)
def test_historical_alert_endpoint_returns_normalized_records(
    internal_api_client,
    bounded_queryset,
    disease,
    expected_disease,
):
    response = internal_api_client.get(
        reverse("api:internal:historical_alerts"),
        {"disease": disease},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["disease"] == expected_disease
    assert payload["results"][0]["municipality_geocode"] == 3304557
    assert (
        payload["results"][0]["epidemiological_week_start_date"]
        == "2026-01-04"
    )


def test_historical_alert_endpoint_passes_typed_inputs_to_real_service(
    internal_api_client,
    bounded_queryset,
    monkeypatch,
):
    captured = {}
    real_get_queryset = views.get_historical_alert_queryset

    def spy_get_queryset(disease, **filters):
        captured["disease"] = disease
        captured["filters"] = filters
        return real_get_queryset(disease, **filters)

    monkeypatch.setattr(
        views, "get_historical_alert_queryset", spy_get_queryset
    )

    response = internal_api_client.get(
        reverse("api:internal:historical_alerts"),
        {
            "disease": "dengue",
            "municipality_geocode": "3304557",
            "epidemiological_week": "202601",
            "start_week": "202601",
            "end_week": "202652",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "alert_level": "2",
            "limit": "10",
            "offset": "3",
            "ordering": "epidemiological_week",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "disease": "dengue",
        "filters": {
            "municipality_geocode": 3304557,
            "epidemiological_week": 202601,
            "start_week": 202601,
            "end_week": 202652,
            "start_date": date(2026, 1, 1),
            "end_date": date(2026, 12, 31),
            "alert_level": 2,
            "limit": 10,
            "offset": 3,
            "ordering": "epidemiological_week",
        },
    }


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"disease": "yellow-fever"},
        {"disease": "dengue", "municipality_geocode": "not-an-int"},
        {"disease": "dengue", "start_date": "2026-99-99"},
        {"disease": "dengue", "start_week": "202652", "end_week": "202601"},
        {
            "disease": "dengue",
            "start_date": "2026-02-01",
            "end_date": "2026-01-01",
        },
        {"disease": "dengue", "ordering": "id; DROP TABLE alerts"},
        {"disease": "dengue", "limit": "-1"},
        {"disease": "dengue", "offset": "-1"},
    ],
)
def test_historical_alert_endpoint_rejects_invalid_input(
    internal_api_client, params
):
    response = internal_api_client.get(
        reverse("api:internal:historical_alerts"), params
    )

    assert response.status_code == 400
    assert "detail" in response.json()


def test_historical_alert_endpoint_never_exposes_legacy_keys(
    internal_api_client,
    bounded_queryset,
):
    response = internal_api_client.get(
        reverse("api:internal:historical_alerts"),
        {"disease": "dengue"},
    )

    result = response.json()["results"][0]
    for legacy_key in (
        "SE",
        "data_iniSE",
        "Localidade_id",
        "municipio_geocodigo",
        "casos_est",
        "p_rt1",
        "p_inc100k",
    ):
        assert legacy_key not in result


def test_historical_alert_endpoint_requires_internal_token(api_client):
    response = api_client.get(
        reverse("api:internal:historical_alerts"),
        {"disease": "dengue"},
    )

    assert response.status_code in {401, 403}
