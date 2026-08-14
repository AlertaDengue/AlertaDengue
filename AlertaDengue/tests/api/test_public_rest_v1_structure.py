from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from api.internal.permissions import HasInternalAPIAccess
from api.internal.views import HistoricalAlertListView
from api.v1.responses import build_error_response, build_success_response
from api.v1.views import PublicAPIRootView


def test_public_rest_v1_root_route_returns_public_api_metadata():
    response = APIClient().get(reverse("api:v1:root"))

    assert response.status_code == 200
    assert response.json() == {
        "api": "public",
        "version": "v1",
        "status": "ok",
        "routes": {},
    }


def test_existing_api_route_names_remain_resolvable():
    assert reverse("api:alertcity") == "/api/alertcity"
    assert reverse("api:internal:historical_alerts") == (
        "/api/internal/historical-alerts/"
    )


def test_public_and_internal_rest_permissions_remain_separate():
    assert PublicAPIRootView.permission_classes == [AllowAny]
    assert HistoricalAlertListView.permission_classes == [HasInternalAPIAccess]
    assert AllowAny not in HistoricalAlertListView.permission_classes


def test_build_success_response_with_data_only():
    assert build_success_response({"city": "Rio"}) == {"data": {"city": "Rio"}}


def test_build_success_response_with_meta():
    assert build_success_response([], meta={"limit": 10}) == {
        "data": [],
        "meta": {"limit": 10},
    }


def test_build_error_response_with_detail_only():
    assert build_error_response("Not found") == {"detail": "Not found"}


def test_build_error_response_with_code():
    assert build_error_response("Not found", code="not_found") == {
        "detail": "Not found",
        "code": "not_found",
    }
