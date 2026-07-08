from pathlib import Path

from django.contrib.auth.models import Group, User
from django.db import connection
from django.urls import reverse
import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from api.internal.constants import NOTIFICATION_API_GROUP_NAME

CURRENT_DIR = Path(__file__).resolve().parent.parent
NOTIFICATION_SQL_FIXTURE = (
    CURRENT_DIR / "datasets" / "test_notification.output.sql"
)


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def notification_api_group(db):
    group, _ = Group.objects.get_or_create(
        name=NOTIFICATION_API_GROUP_NAME,
    )
    return group


@pytest.fixture()
def notification_api_client(db, api_client, notification_api_group):
    user = User.objects.create_user(
        username="notification-api-user",
        password="test-password",
    )
    user.groups.add(notification_api_group)

    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    return api_client


@pytest.fixture()
def unauthorized_api_client(db, api_client):
    user = User.objects.create_user(
        username="regular-user",
        password="test-password",
    )

    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    return api_client


@pytest.fixture()
def notification_data(db):
    sql = NOTIFICATION_SQL_FIXTURE.read_text(encoding="utf-8")

    with connection.cursor() as cursor:
        cursor.execute(sql)


@pytest.mark.django_db
def test_notifications_endpoint_requires_auth(api_client):
    url = reverse("api:internal:notifications")

    response = api_client.get(url)

    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_notifications_endpoint_rejects_user_without_group(
    unauthorized_api_client,
):
    url = reverse("api:internal:notifications")

    response = unauthorized_api_client.get(url)

    assert response.status_code == 403


@pytest.mark.django_db
def test_notifications_endpoint_allows_user_with_group(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "municipio_geocodigo": 3304557,
            "cid10": "A90",
            "year": 2024,
            "limit": 10,
            "offset": 0,
            "include_count": "true",
        },
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_notifications_endpoint_exists(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {"limit": 1, "offset": 0},
    )

    assert response.status_code != 404


@pytest.mark.django_db
def test_notifications_endpoint_returns_paginated_payload(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "municipio_geocodigo": 3304557,
            "cid10": "A90",
            "year": 2024,
            "limit": 1000,
            "offset": 0,
            "include_count": "true",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 2
    assert payload["limit"] == 1000
    assert payload["offset"] == 0
    assert len(payload["results"]) == 2

    first_result = payload["results"][0]

    assert first_result["id"] == 2
    assert first_result["dt_notific"] == "2024-02-15"
    assert first_result["dt_sin_pri"] == "2024-02-10"
    assert first_result["dt_digita"] == "2024-02-16"
    assert first_result["se_notif"] == 7
    assert first_result["ano_notif"] == 2024
    assert first_result["municipio_geocodigo"] == 3304557
    assert float(first_result["id_distrit"]) == 1.0
    assert float(first_result["id_bairro"]) == 11.0
    assert first_result["nm_bairro"] == "Copacabana"
    assert first_result["nu_notific"] == 123457
    assert first_result["cid10_codigo"] == "A90"
    assert float(first_result["classi_fin"]) == 2.0
    assert float(first_result["criterio"]) == 2.0


@pytest.mark.django_db
def test_notifications_endpoint_filters_by_municipio_geocodigo(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "municipio_geocodigo": 3550308,
            "limit": 1000,
            "offset": 0,
            "include_count": "true",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["municipio_geocodigo"] == 3550308


@pytest.mark.django_db
def test_notifications_endpoint_filters_by_cid10(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "cid10": "A92",
            "limit": 1000,
            "offset": 0,
            "include_count": "true",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["cid10_codigo"] == "A92"


@pytest.mark.django_db
def test_notifications_endpoint_filters_by_year(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "year": 2023,
            "limit": 1000,
            "offset": 0,
            "include_count": "true",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["ano_notif"] == 2023


@pytest.mark.django_db
def test_notifications_endpoint_filters_by_epiweek_range(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "year": 2024,
            "epiweek_start": 1,
            "epiweek_end": 3,
            "limit": 1000,
            "offset": 0,
            "include_count": "true",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["se_notif"] == 2


@pytest.mark.django_db
def test_notifications_endpoint_filters_by_date_range(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "date_start": "2024-02-01",
            "date_end": "2024-02-28",
            "limit": 1000,
            "offset": 0,
            "include_count": "true",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["dt_notific"] == "2024-02-15"


@pytest.mark.django_db
def test_notifications_endpoint_applies_limit_and_offset(
    notification_api_client,
    notification_data,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(
        url,
        {
            "municipio_geocodigo": 3304557,
            "cid10": "A90",
            "year": 2024,
            "limit": 1,
            "offset": 1,
            "include_count": "true",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["count"] == 2
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["id"] == 1


@pytest.mark.django_db
def test_notifications_endpoint_returns_400_for_invalid_limit(
    notification_api_client,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(url, {"limit": 0})

    assert response.status_code == 400


@pytest.mark.django_db
def test_notifications_endpoint_returns_400_for_invalid_offset(
    notification_api_client,
):
    url = reverse("api:internal:notifications")

    response = notification_api_client.get(url, {"offset": -1})

    assert response.status_code == 400
