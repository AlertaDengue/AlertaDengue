"""Lookup helpers for the separate legacy historical-alert adapters."""

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


def get_latest_historical_alert_week(disease: str) -> int | None:
    """Return the newest epidemiological week through the ORM adapter.

    This intentionally exposes the normalized service operation rather than
    the legacy ``SE`` database column used by the retained tables.
    """
    model = get_legacy_historical_alert_model(disease)
    return (
        model.objects.order_by("-epidemiological_week_start_date")
        .values_list("epidemiological_week", flat=True)
        .first()
    )
