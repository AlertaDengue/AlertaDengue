# api/internal/services.py

from datetime import date, datetime
from decimal import Decimal
import math
from typing import Any

from django.db.models import BigIntegerField, F, FloatField, QuerySet
from django.db.models.functions import Cast

from dados.models import Notification

from .schemas import NotificationQueryParams


def normalize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, Decimal):
        if not value.is_finite():
            return None
        return float(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return value


def build_notification_queryset(
    params: NotificationQueryParams,
) -> QuerySet[Notification]:
    """Build the bounded internal notification query on the ``dados`` alias."""
    queryset = Notification.objects.using("dados").all()
    if params.municipio_geocodigo is not None:
        queryset = queryset.filter(
            municipality_geocode=params.municipio_geocodigo
        )

    if params.cid10:
        queryset = queryset.filter(cid10_code=params.cid10)

    if params.year is not None:
        queryset = queryset.filter(notification_year=params.year)

    if params.epiweek_start is not None:
        queryset = queryset.filter(notification_week__gte=params.epiweek_start)

    if params.epiweek_end is not None:
        queryset = queryset.filter(notification_week__lte=params.epiweek_end)

    if params.date_start:
        queryset = queryset.filter(notification_date__gte=params.date_start)

    if params.date_end:
        queryset = queryset.filter(notification_date__lte=params.date_end)

    return queryset.order_by("-notification_date", "-id")


def get_notification_response_queryset(
    params: NotificationQueryParams,
) -> QuerySet:
    """Project ORM fields to the established internal API response keys."""
    return build_notification_queryset(params).values(
        "id",
        municipio_geocodigo=F("municipality_geocode"),
        dt_notific=F("notification_date"),
        dt_sin_pri=F("symptom_onset_date"),
        dt_digita=F("entry_date"),
        se_notif=F("notification_week"),
        ano_notif=F("notification_year"),
        classi_fin=Cast("final_classification", FloatField()),
        criterio=Cast("criteria", FloatField()),
        cid10_codigo=F("cid10_code"),
        id_distrit=Cast("district_id", FloatField()),
        id_bairro=Cast("neighborhood_id", FloatField()),
        nm_bairro=F("neighborhood_name"),
        nu_notific=Cast("notification_number", BigIntegerField()),
    )


def list_notifications(query_params: dict[str, Any]) -> dict[str, Any]:
    params = NotificationQueryParams.model_validate(
        query_params.dict() if hasattr(query_params, "dict") else query_params
    )

    queryset = get_notification_response_queryset(params)
    results = [
        {key: normalize_value(value) for key, value in record.items()}
        for record in queryset[params.offset : params.offset + params.limit]
    ]

    payload: dict[str, Any] = {
        "limit": params.limit,
        "offset": params.offset,
        "results": results,
    }

    if params.include_count:
        payload["count"] = queryset.count()

    return payload
