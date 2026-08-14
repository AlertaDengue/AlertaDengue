from unittest.mock import MagicMock

from django.urls import reverse
import pandas as pd
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from api import views as legacy_views
from api.internal.permissions import HasInternalAPIAccess
from api.internal.views import HistoricalAlertListView
from api.v1 import views
from api.v1.views import PublicAlertCityView, PublicEpiYearWeekView


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


def test_v1_alert_city_uses_real_alert_city_service(monkeypatch):
    search = MagicMock(
        return_value=pd.DataFrame(
            [{"SE": 202601, "municipio_geocodigo": 3304557, "casos": 3}]
        )
    )
    monkeypatch.setattr(views.AlertCity, "search", search)
    response = APIClient().get(
        reverse("api:v1:alert_city"),
        {"disease": "dengue", "geocode": "3304557"},
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["epidemiological_week"] == 202601
    assert response.json()["data"][0]["municipality_geocode"] == 3304557
    search.assert_called_once()


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


def test_v1_csv_delegates_to_legacy_response(monkeypatch):
    query = MagicMock()
    query.get_disease_dist.return_value.to_csv.return_value = (
        "category,casos\n"
    )
    monkeypatch.setattr(
        legacy_views,
        "NotificationQueries",
        lambda **kwargs: query,
    )
    response = APIClient().get(
        reverse("api:v1:notification_reduced_csv"),
        {"state_abv": "RJ", "chart_type": "disease"},
    )
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
