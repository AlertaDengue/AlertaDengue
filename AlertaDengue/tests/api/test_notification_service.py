from datetime import date

from django.db import connections
from django.test.utils import CaptureQueriesContext
import pytest

from api.internal.schemas import NotificationQueryParams
from api.internal.services import (
    build_notification_queryset,
    list_notifications,
)
from dados.models import Notification

pytestmark = pytest.mark.django_db(
    databases={"default", "dados"}, transaction=True
)


@pytest.mark.usefixtures("notification_table")
def test_notification_service_matches_the_legacy_list_contract():
    payload = list_notifications(
        {
            "municipio_geocodigo": 3304557,
            "cid10": "A90",
            "year": 2024,
            "epiweek_start": 1,
            "epiweek_end": 10,
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "limit": 1,
            "offset": 1,
            "include_count": True,
        }
    )

    assert payload == {
        "limit": 1,
        "offset": 1,
        "count": 2,
        "results": [
            {
                "id": 1,
                "municipio_geocodigo": 3304557,
                "dt_notific": "2024-01-10",
                "dt_sin_pri": "2024-01-08",
                "dt_digita": "2024-01-12",
                "se_notif": 2,
                "ano_notif": 2024,
                "classi_fin": 1.0,
                "criterio": 1.0,
                "cid10_codigo": "A90",
                "id_distrit": 1.0,
                "id_bairro": 10.0,
                "nm_bairro": "Centro",
                "nu_notific": 123456,
            }
        ],
    }


@pytest.mark.usefixtures("notification_table")
def test_notification_service_preserves_null_values_and_empty_results():
    null_payload = list_notifications({"cid10": "A92"})
    empty_payload = list_notifications({"municipio_geocodigo": 9999999})

    assert null_payload["results"][0]["classi_fin"] is None
    assert null_payload["results"][0]["criterio"] is None
    assert empty_payload == {"limit": 1000, "offset": 0, "results": []}


def test_notification_queryset_uses_dados_and_the_legacy_ordering():
    queryset = build_notification_queryset(
        NotificationQueryParams(
            municipio_geocodigo=3304557,
            cid10="A90",
            year=2024,
            epiweek_start=1,
            epiweek_end=10,
            date_start=date(2024, 1, 1),
            date_end=date(2024, 12, 31),
        )
    )
    sql = str(queryset.query)

    assert queryset.model is Notification
    assert queryset.db == "dados"
    assert '"Municipio"."Notificacao"' in sql
    assert '"municipio_geocodigo"' in sql
    assert '"cid10_codigo"' in sql
    assert '"ano_notif"' in sql
    assert '"se_notif"' in sql
    assert '"dt_notific"' in sql
    assert '"dt_notific" DESC' in sql
    assert '"id" DESC' in sql


@pytest.mark.usefixtures("notification_table")
def test_notification_service_uses_one_dados_query_without_count():
    with CaptureQueriesContext(connections["dados"]) as captured:
        payload = list_notifications({"limit": 1})

    assert len(captured) == 1
    assert len(payload["results"]) == 1
    assert '"Municipio"."Notificacao"' in captured[0]["sql"]


@pytest.mark.usefixtures("notification_table")
def test_notification_service_uses_two_dados_queries_with_count_and_pagination():
    with CaptureQueriesContext(connections["dados"]) as captured:
        payload = list_notifications(
            {
                "municipio_geocodigo": 3304557,
                "limit": 1,
                "offset": 1,
                "include_count": True,
            }
        )

    assert len(captured) == 2
    assert payload["count"] == 2
    assert payload["results"][0]["id"] == 1
    assert all(
        '"Municipio"."Notificacao"' in query["sql"]
        for query in captured.captured_queries
    )
    assert "LIMIT 1 OFFSET 1" in captured[0]["sql"]


@pytest.mark.usefixtures("notification_table")
def test_notification_service_never_reads_notification_records_from_default():
    with CaptureQueriesContext(connections["default"]) as default_queries:
        list_notifications({"limit": 1})

    assert not any(
        '"Municipio"."Notificacao"' in query["sql"]
        for query in default_queries.captured_queries
    )
