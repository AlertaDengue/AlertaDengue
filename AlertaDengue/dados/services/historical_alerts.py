"""Lookup helpers for the separate legacy historical-alert adapters."""

from django.db.models import Case, CharField, F, QuerySet, Value, When

from dados.models.municipio import (
    LegacyHistoricalAlertChikungunya,
    LegacyHistoricalAlertDengue,
    LegacyHistoricalAlertZika,
)

_MODELS = {
    "dengue": LegacyHistoricalAlertDengue,
    "chikungunya": LegacyHistoricalAlertChikungunya,
    "zika": LegacyHistoricalAlertZika,
}
_ALIASES = {"chik": "chikungunya"}


def get_supported_historical_alert_diseases() -> tuple[str, ...]:
    return tuple(_MODELS)


def normalize_disease_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = _ALIASES.get(normalized, normalized)
    if normalized not in _MODELS:
        supported = ", ".join(("dengue", "chik", "chikungunya", "zika"))
        raise ValueError(
            f"Unsupported disease {value!r}; supported values: {supported}"
        )
    return normalized


def get_legacy_historical_alert_model(disease: str):
    return _MODELS[normalize_disease_key(disease)]


def get_legacy_historical_alert_table_name(disease: str) -> str:
    return get_legacy_historical_alert_model(disease)._meta.db_table


def build_historical_alert_records_queryset(
    *,
    disease: str,
    municipality_geocode: int,
    start_week: int | None = None,
    end_week: int | None = None,
):
    """Return public-record candidates from the selected retained table."""
    model = get_legacy_historical_alert_model(disease)
    queryset = model.objects.filter(municipality_geocode=municipality_geocode)

    if start_week is not None:
        queryset = queryset.filter(epidemiological_week__gte=start_week)
    if end_week is not None:
        queryset = queryset.filter(epidemiological_week__lte=end_week)

    return queryset.order_by(
        "epidemiological_week_start_date", "epidemiological_week", "id"
    )


def build_report_city_historical_alert_queryset(
    *,
    disease: str,
    municipality_geocode: int,
    start_week: int,
    end_week: int,
) -> QuerySet:
    """Return the bounded projection used by the city-report charts.

    This preserves the legacy ``ReportCity`` range and 200-row limit while
    keeping filtering, projection, ordering, and limiting on the ``dados``
    PostgreSQL connection.
    """
    model = get_legacy_historical_alert_model(disease)
    alert_label = Case(
        When(alert_level=1, then=Value("verde")),
        When(alert_level=2, then=Value("amarelo")),
        When(alert_level=3, then=Value("laranja")),
        When(alert_level=4, then=Value("vermelho")),
        default=Value("-"),
        output_field=CharField(),
    )
    return (
        model.objects.using("dados")
        .filter(
            municipality_geocode=municipality_geocode,
            epidemiological_week__range=(start_week, end_week),
        )
        .annotate(
            report_week=F("epidemiological_week"),
            notified_cases=F("cases"),
            incidence=F("incidence_100k_probability"),
            incidence_rise_probability=F("rt1_probability"),
            minimum_temperature=F("temperature_min"),
            mean_temperature=F("temperature_mean"),
            maximum_temperature=F("temperature_max"),
            minimum_humidity=F("humidity_min"),
            mean_humidity=F("humidity_mean"),
            maximum_humidity=F("humidity_max"),
            alert_label=alert_label,
            level_code=F("alert_level"),
        )
        .order_by("epidemiological_week")
        .values(
            "report_week",
            "notified_cases",
            "estimated_cases",
            "incidence",
            "incidence_rise_probability",
            "minimum_temperature",
            "mean_temperature",
            "maximum_temperature",
            "minimum_humidity",
            "mean_humidity",
            "maximum_humidity",
            "alert_label",
            "level_code",
        )[:200]
    )


def get_latest_historical_alert_week(disease: str) -> int | None:
    """Return the newest epidemiological week through the ORM adapter.

    This intentionally exposes the normalized service operation rather than
    the legacy ``SE`` database column used by the retained tables.
    """
    model = get_legacy_historical_alert_model(disease)
    return (
        model.objects.order_by(
            "-epidemiological_week_start_date",
            "-epidemiological_week",
        )
        .values_list("epidemiological_week", flat=True)
        .first()
    )
