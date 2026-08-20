"""Service boundaries for the public REST API v1 surface."""

from datetime import date, datetime
from typing import Any

import pandas as pd

from dados.services.historical_alerts import (
    build_historical_alert_records_queryset,
)

__all__ = [
    "ALERT_CITY_FIELD_MAP",
    "ALERT_CITY_RESPONSE_FIELDS",
    "get_public_alert_city_records",
    "normalize_public_alert_city_records",
    "serialize_public_alert_city_record",
]


ALERT_CITY_FIELD_MAP = {
    "data_iniSE": "epidemiological_week_start_date",
    "SE": "epidemiological_week",
    "casos_est": "estimated_cases",
    "casos_est_min": "estimated_cases_min",
    "casos_est_max": "estimated_cases_max",
    "casos": "cases",
    "municipio_geocodigo": "municipality_geocode",
    "municipio_nome": "municipality_name",
    "p_rt1": "rt1_probability",
    "p_inc100k": "incidence_100k_probability",
    "Localidade_id": "locality_id",
    "nivel": "alert_level",
    "id": "id",
    "versao_modelo": "model_version",
    "Rt": "reproduction_number",
    "pop": "population",
    "tempmin": "temperature_min",
    "tempmed": "temperature_mean",
    "tempmax": "temperature_max",
    "umidmin": "humidity_min",
    "umidmed": "humidity_mean",
    "umidmax": "humidity_max",
    "receptivo": "receptive",
    "transmissao": "transmission",
    "nivel_inc": "incidence_level",
    "casprov": "probable_cases",
    "casprov_est": "estimated_probable_cases",
    "casprov_est_min": "estimated_probable_cases_min",
    "casprov_est_max": "estimated_probable_cases_max",
    "casconf": "confirmed_cases",
    "notif_accum_year": "notifications_accumulated_year",
}
ALERT_CITY_RESPONSE_FIELDS = tuple(ALERT_CITY_FIELD_MAP.values())


def normalize_public_alert_city_records(
    records: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Return the allowlisted, JSON-safe public v1 alert-city records."""
    normalized_records = []
    for record in records.rename(columns=ALERT_CITY_FIELD_MAP).to_dict(
        "records"
    ):
        normalized_record: dict[str, Any] = {}
        for field in ALERT_CITY_RESPONSE_FIELDS:
            if field not in record:
                continue
            value = record[field]
            if value is None or pd.isna(value):
                normalized_record[field] = None
            elif hasattr(value, "item"):
                value = value.item()

                if isinstance(value, (date, datetime, pd.Timestamp)):
                    normalized_record[field] = value.isoformat()
                else:
                    normalized_record[field] = value
            elif isinstance(value, (date, datetime, pd.Timestamp)):
                normalized_record[field] = value.isoformat()
            else:
                normalized_record[field] = value
        normalized_records.append(normalized_record)
    return normalized_records


def get_public_alert_city_records(
    *,
    disease: str,
    geocode: str | int | None,
    ew_start: int | None,
    ew_end: int | None,
) -> list[dict[str, Any]]:
    """Fetch and normalize alert-city records for the public v1 contract."""
    if geocode is None:
        raise ValueError("geocode is required")
    queryset = build_historical_alert_records_queryset(
        disease=disease,
        municipality_geocode=int(geocode),
        start_week=ew_start,
        end_week=ew_end,
    )
    return [serialize_public_alert_city_record(record) for record in queryset]


def serialize_public_alert_city_record(record: Any) -> dict[str, Any]:
    """Serialize an ORM adapter row using only public v1 field names."""
    serialized: dict[str, Any] = {}
    for field in ALERT_CITY_RESPONSE_FIELDS:
        value = getattr(record, field, None)
        if field == "epidemiological_week_start_date" and isinstance(
            value, date
        ):
            serialized[field] = datetime.combine(
                value, datetime.min.time()
            ).isoformat()
        elif isinstance(value, datetime):
            serialized[field] = value.isoformat()
        else:
            serialized[field] = value
    return serialized
