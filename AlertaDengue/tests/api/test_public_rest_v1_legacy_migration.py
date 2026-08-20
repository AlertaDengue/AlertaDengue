from datetime import date

from django.db import connections
from django.urls import reverse
import numpy as np
import pandas as pd
import pytest
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from api.internal.permissions import HasInternalAPIAccess
from api.internal.views import HistoricalAlertListView
from api.v1.services import (
    ALERT_CITY_RESPONSE_FIELDS,
    get_public_alert_city_records,
    normalize_public_alert_city_records,
)
from api.v1.views import (
    PublicAlertCityView,
    PublicEpiYearWeekView,
    PublicNotificationReducedCSVView,
)
from api.views import NotificationReducedCSV_View
from dados.models import (
    LegacyHistoricalAlertChikungunya,
    LegacyHistoricalAlertDengue,
    LegacyHistoricalAlertZika,
)


@pytest.fixture
def public_historical_alert_tables():
    """Create the unmanaged alert tables used by the public v1 service."""
    database_connection = connections["dados"]
    if database_connection.vendor != "postgresql":
        pytest.skip("historical alert adapters require PostgreSQL schemas")

    models = (
        LegacyHistoricalAlertDengue,
        LegacyHistoricalAlertChikungunya,
        LegacyHistoricalAlertZika,
    )
    with database_connection.cursor() as cursor:
        cursor.execute('CREATE SCHEMA IF NOT EXISTS "Municipio"')
        for model in reversed(models):
            cursor.execute(
                f"DROP TABLE IF EXISTS {model._meta.db_table} CASCADE"
            )
    with database_connection.schema_editor() as schema_editor:
        for model in models:
            schema_editor.create_model(model)

    yield

    with database_connection.cursor() as cursor:
        for model in reversed(models):
            cursor.execute(
                f"DROP TABLE IF EXISTS {model._meta.db_table} CASCADE"
            )


@pytest.mark.django_db(databases={"default", "dados"}, transaction=True)
@pytest.mark.parametrize(
    ("disease", "model"),
    [
        ("dengue", LegacyHistoricalAlertDengue),
        ("chik", LegacyHistoricalAlertChikungunya),
        ("zika", LegacyHistoricalAlertZika),
    ],
)
def test_public_alert_city_service_uses_orm_disease_filtering_and_ordering(
    public_historical_alert_tables, disease, model
):
    other_model = (
        LegacyHistoricalAlertZika
        if model is not LegacyHistoricalAlertZika
        else LegacyHistoricalAlertDengue
    )
    second = model.objects.create(
        epidemiological_week_start_date=date(2026, 1, 11),
        epidemiological_week=202602,
        municipality_geocode=3304557,
        municipality_name="Rio",
    )
    first = model.objects.create(
        epidemiological_week_start_date=date(2026, 1, 4),
        epidemiological_week=202601,
        municipality_geocode=3304557,
        municipality_name="Rio",
    )
    model.objects.create(
        epidemiological_week_start_date=date(2026, 1, 4),
        epidemiological_week=202601,
        municipality_geocode=9999999,
    )
    other_model.objects.create(
        epidemiological_week_start_date=date(2026, 1, 4),
        epidemiological_week=202601,
        municipality_geocode=3304557,
    )

    records = get_public_alert_city_records(
        disease=disease, geocode=3304557, ew_start=202601, ew_end=202602
    )

    assert [record["id"] for record in records] == [first.id, second.id]
    assert all(
        set(record) == set(ALERT_CITY_RESPONSE_FIELDS) for record in records
    )
    assert "tweet" not in records[0]
    assert not {"SE", "data_iniSE", "municipio_geocodigo"} & set(records[0])


@pytest.mark.django_db(databases={"default", "dados"}, transaction=True)
def test_public_alert_city_service_serializes_all_mapped_fields(
    public_historical_alert_tables,
):
    alert = LegacyHistoricalAlertDengue.objects.create(
        epidemiological_week_start_date=date(2026, 1, 4),
        epidemiological_week=202601,
        estimated_cases=10.5,
        estimated_cases_min=8,
        estimated_cases_max=13,
        cases=3,
        municipality_geocode=3304557,
        municipality_name="Rio de Janeiro",
        rt1_probability=0.9,
        incidence_100k_probability=0.8,
        locality_id=1,
        alert_level=2,
        model_version="v1",
        reproduction_number=1.2,
        population=6200000,
        temperature_min=20.1,
        temperature_mean=25.2,
        temperature_max=30.3,
        humidity_min=40.1,
        humidity_mean=55.2,
        humidity_max=70.3,
        receptive=1,
        transmission=1,
        incidence_level=3,
        probable_cases=4,
        estimated_probable_cases=5.5,
        estimated_probable_cases_min=4,
        estimated_probable_cases_max=6,
        confirmed_cases=2,
    )

    record = get_public_alert_city_records(
        disease="dengue", geocode=3304557, ew_start=None, ew_end=None
    )[0]

    assert record == {
        "epidemiological_week_start_date": "2026-01-04T00:00:00",
        "epidemiological_week": 202601,
        "estimated_cases": 10.5,
        "estimated_cases_min": 8,
        "estimated_cases_max": 13,
        "cases": 3,
        "municipality_geocode": 3304557,
        "municipality_name": "Rio de Janeiro",
        "rt1_probability": 0.9,
        "incidence_100k_probability": 0.8,
        "locality_id": 1,
        "alert_level": 2,
        "id": alert.id,
        "model_version": "v1",
        "reproduction_number": 1.2,
        "population": 6200000,
        "temperature_min": 20.1,
        "temperature_mean": 25.2,
        "temperature_max": 30.3,
        "humidity_min": 40.1,
        "humidity_mean": 55.2,
        "humidity_max": 70.3,
        "receptive": 1,
        "transmission": 1,
        "incidence_level": 3,
        "probable_cases": 4,
        "estimated_probable_cases": 5.5,
        "estimated_probable_cases_min": 4,
        "estimated_probable_cases_max": 6,
        "confirmed_cases": 2,
        "notifications_accumulated_year": None,
    }


@pytest.mark.django_db(databases={"default", "dados"}, transaction=True)
def test_public_alert_city_route_reads_inserted_orm_record(
    public_historical_alert_tables,
):
    LegacyHistoricalAlertDengue.objects.create(
        epidemiological_week_start_date=date(2026, 1, 4),
        epidemiological_week=202601,
        municipality_geocode=3304557,
    )

    response = APIClient().get(
        reverse("api:v1:alert_city"),
        {"disease": "dengue", "geocode": 3304557},
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["municipality_geocode"] == 3304557


def test_v1_and_legacy_routes_resolve():
    assert reverse("api:v1:alert_city") == "/api/v1/alert-city/"
    assert reverse("api:v1:epi_year_week") == "/api/v1/epi-year-week/"
    assert reverse("api:v1:notification_reduced_csv").endswith("reduced.csv")
    assert reverse("api:alertcity") == "/api/alertcity"


def test_v1_root_regression():
    assert APIClient().get(reverse("api:v1:root")).status_code == 200


def test_public_and_internal_permissions_remain_separate():
    assert PublicAlertCityView.permission_classes == [AllowAny]
    assert PublicEpiYearWeekView.permission_classes == [AllowAny]
    assert HistoricalAlertListView.permission_classes == [HasInternalAPIAccess]


def test_public_alert_city_normalizes_allowlisted_legacy_fields():
    legacy_record = {
        "data_iniSE": pd.Timestamp("2026-01-04"),
        "SE": np.int64(202601),
        "casos_est": 10.5,
        "casos_est_min": 8.0,
        "casos_est_max": 13.0,
        "casos": np.int64(3),
        "municipio_geocodigo": np.int64(3304557),
        "municipio_nome": "Rio de Janeiro",
        "p_rt1": 0.9,
        "p_inc100k": 0.8,
        "Localidade_id": np.int64(1),
        "nivel": np.int64(2),
        "id": np.int64(99),
        "versao_modelo": "v1",
        "Rt": 1.2,
        "pop": np.int64(6200000),
        "tempmin": 20.1,
        "tempmed": 25.2,
        "tempmax": 30.3,
        "umidmin": 40.1,
        "umidmed": 55.2,
        "umidmax": 70.3,
        "receptivo": 1,
        "transmissao": 1,
        "nivel_inc": 3,
        "casprov": 4,
        "casprov_est": 5.5,
        "casprov_est_min": 4.5,
        "casprov_est_max": 6.5,
        "casconf": 2,
        "notif_accum_year": 12,
        "tweet": "excluded",
        "unmapped_field": "excluded",
    }
    record = normalize_public_alert_city_records(
        pd.DataFrame([legacy_record])
    )[0]
    assert set(record) == set(ALERT_CITY_RESPONSE_FIELDS)
    assert record == {
        "epidemiological_week_start_date": "2026-01-04T00:00:00",
        "epidemiological_week": 202601,
        "estimated_cases": 10.5,
        "estimated_cases_min": 8.0,
        "estimated_cases_max": 13.0,
        "cases": 3,
        "municipality_geocode": 3304557,
        "municipality_name": "Rio de Janeiro",
        "rt1_probability": 0.9,
        "incidence_100k_probability": 0.8,
        "locality_id": 1,
        "alert_level": 2,
        "id": 99,
        "model_version": "v1",
        "reproduction_number": 1.2,
        "population": 6200000,
        "temperature_min": 20.1,
        "temperature_mean": 25.2,
        "temperature_max": 30.3,
        "humidity_min": 40.1,
        "humidity_mean": 55.2,
        "humidity_max": 70.3,
        "receptive": 1,
        "transmission": 1,
        "incidence_level": 3,
        "probable_cases": 4,
        "estimated_probable_cases": 5.5,
        "estimated_probable_cases_min": 4.5,
        "estimated_probable_cases_max": 6.5,
        "confirmed_cases": 2,
        "notifications_accumulated_year": 12,
    }
    assert "tweet" not in record
    assert not {
        "data_iniSE",
        "SE",
        "casos_est",
        "casos_est_min",
        "casos_est_max",
        "casos",
        "municipio_geocodigo",
        "municipio_nome",
        "p_rt1",
        "p_inc100k",
        "Localidade_id",
        "nivel",
        "versao_modelo",
        "Rt",
        "pop",
        "tempmin",
        "tempmed",
        "tempmax",
        "umidmin",
        "umidmed",
        "umidmax",
        "receptivo",
        "transmissao",
        "nivel_inc",
        "casprov",
        "casprov_est",
        "casprov_est_min",
        "casprov_est_max",
        "casconf",
        "notif_accum_year",
        "unmapped_field",
    } & set(record)


def test_public_alert_city_normalizes_pandas_and_numpy_values():
    record = normalize_public_alert_city_records(
        pd.DataFrame(
            [
                {
                    "SE": np.int64(202601),
                    "data_iniSE": pd.Timestamp("2026-01-04"),
                    "casos": np.nan,
                    "nivel": pd.NaT,
                }
            ]
        )
    )[0]

    assert record["epidemiological_week_start_date"] == "2026-01-04T00:00:00"
    assert record["epidemiological_week"] == 202601
    assert record["cases"] is None
    assert record["alert_level"] is None


def test_v1_epi_year_week_returns_normalized_response():
    response = APIClient().get(
        reverse("api:v1:epi_year_week"), {"epidate": "2026-01-04"}
    )
    assert response.status_code == 200
    assert "epidemiological_week" in response.json()["data"]


def test_v1_json_errors_use_response_helper_shape():
    response = APIClient().get(reverse("api:v1:epi_year_week"))
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_query"


def test_v1_csv_preserves_legacy_response_class():
    assert issubclass(
        PublicNotificationReducedCSVView, NotificationReducedCSV_View
    )
    assert PublicNotificationReducedCSVView.permission_classes == [AllowAny]
