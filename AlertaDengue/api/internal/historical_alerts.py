"""Bounded ORM access to the retained historical-alert tables.

The three legacy tables remain separate and unmanaged.  This module provides
the normalized interface intended for future internal REST endpoints.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from django.db.models import Model, QuerySet

from dados.services.historical_alerts import (
    get_legacy_historical_alert_model,
    normalize_disease_key,
)

DEFAULT_HISTORICAL_ALERT_LIMIT = 1000
MAX_HISTORICAL_ALERT_LIMIT = 5000

_ORDERING_FIELDS = frozenset(
    {
        "alert_level",
        "epidemiological_week",
        "epidemiological_week_start_date",
        "estimated_cases",
        "municipality_geocode",
    }
)
_RESPONSE_FIELDS = (
    "disease",
    "municipality_geocode",
    "municipality_name",
    "epidemiological_week",
    "epidemiological_week_start_date",
    "estimated_cases",
    "estimated_cases_min",
    "estimated_cases_max",
    "cases",
    "probable_cases",
    "confirmed_cases",
    "alert_level",
    "model_version",
    "rt1_probability",
    "incidence_100k_probability",
)


@dataclass(frozen=True)
class HistoricalAlertFilters:
    """Validated filters for a bounded historical-alert query.

    Parameters
    ----------
    disease
        Dengue, chik/chikungunya, or zika.
    """

    disease: str
    municipality_geocode: int | None = None
    epidemiological_week: int | None = None
    start_week: int | None = None
    end_week: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    alert_level: int | None = None
    limit: int = DEFAULT_HISTORICAL_ALERT_LIMIT
    offset: int = 0
    ordering: str = "-epidemiological_week"

    def __post_init__(self) -> None:
        """Normalize and validate the supplied service-layer inputs."""
        object.__setattr__(
            self, "disease", normalize_disease_key(self.disease)
        )

        if self.start_week is not None and self.end_week is not None:
            if self.start_week > self.end_week:
                raise ValueError("start_week cannot be greater than end_week")
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("start_date cannot be greater than end_date")
        if self.limit < 0:
            raise ValueError("limit cannot be negative")
        if self.limit > MAX_HISTORICAL_ALERT_LIMIT:
            raise ValueError(
                f"limit cannot exceed {MAX_HISTORICAL_ALERT_LIMIT}"
            )
        if self.offset < 0:
            raise ValueError("offset cannot be negative")
        if self.ordering.lstrip("-") not in _ORDERING_FIELDS:
            raise ValueError("unsupported historical-alert ordering field")


def build_historical_alert_queryset(
    filters: HistoricalAlertFilters,
) -> QuerySet:
    """Build a bounded, unevaluated QuerySet for historical alerts.

    The model selection is delegated to the retained #1063 adapter helper,
    so callers never route to legacy table names directly.
    """
    model = get_legacy_historical_alert_model(filters.disease)
    queryset = model.objects.all()

    if filters.municipality_geocode is not None:
        queryset = queryset.filter(
            municipality_geocode=filters.municipality_geocode
        )
    if filters.epidemiological_week is not None:
        queryset = queryset.filter(
            epidemiological_week=filters.epidemiological_week
        )
    if filters.start_week is not None:
        queryset = queryset.filter(
            epidemiological_week__gte=filters.start_week
        )
    if filters.end_week is not None:
        queryset = queryset.filter(epidemiological_week__lte=filters.end_week)
    if filters.start_date is not None:
        queryset = queryset.filter(
            epidemiological_week_start_date__gte=filters.start_date
        )
    if filters.end_date is not None:
        queryset = queryset.filter(
            epidemiological_week_start_date__lte=filters.end_date
        )
    if filters.alert_level is not None:
        queryset = queryset.filter(alert_level=filters.alert_level)

    return queryset.order_by(filters.ordering)[
        filters.offset : filters.offset + filters.limit
    ]


def get_historical_alert_queryset(
    disease: str,
    **filters: Any,
) -> QuerySet:
    """Construct a bounded historical-alert QuerySet from API-ready inputs."""
    return build_historical_alert_queryset(
        HistoricalAlertFilters(disease=disease, **filters)
    )


def get_historical_alert_response_fields() -> tuple[str, ...]:
    """Return the normalized field names exposed by this service."""
    return _RESPONSE_FIELDS


def serialize_historical_alert(
    record: Model | Mapping[str, Any], disease: str
) -> dict[str, Any]:
    """Serialize an alert model instance or mapping with normalized keys."""
    normalized_disease = normalize_disease_key(disease)
    serialized = {"disease": normalized_disease}
    for field in _RESPONSE_FIELDS[1:]:
        value = (
            record.get(field)
            if isinstance(record, Mapping)
            else getattr(record, field, None)
        )
        serialized[field] = (
            value.isoformat() if isinstance(value, (date, datetime)) else value
        )
    return serialized
