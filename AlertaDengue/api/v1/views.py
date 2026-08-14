"""Views for the public REST API v1 surface."""

from datetime import datetime
from typing import Any

import pandas as pd
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.db import AlertCity
from api.v1.responses import build_error_response, build_success_response
from api.views import NotificationReducedCSV_View
from dados.episem import episem


def normalize_alert_city_records(
    records: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Convert DataFrame values to JSON-safe normalized API records."""
    normalized_records = []
    for record in records.to_dict("records"):
        normalized_record: dict[str, Any] = {}
        for field, value in record.items():
            if value is None or pd.isna(value):
                normalized_record[field] = None
            elif isinstance(value, (datetime, pd.Timestamp)):
                normalized_record[field] = value.isoformat()
            elif hasattr(value, "item"):
                normalized_record[field] = value.item()
            else:
                normalized_record[field] = value
        normalized_records.append(normalized_record)
    return normalized_records


class PublicAPIRootView(APIView):
    """Describe the available public REST API v1 surface."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return the public API version and currently available routes."""
        return Response(
            {
                "api": "public",
                "version": "v1",
                "status": "ok",
                "routes": {},
            }
        )


class PublicAlertCityView(APIView):
    """Return normalized city-alert records through the legacy query service."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            disease = request.query_params["disease"].lower()
            geocode = int(request.query_params["geocode"])
            ew_start = request.query_params.get("ew_start")
            ew_end = request.query_params.get("ew_end")
            records = AlertCity.search(
                disease,
                geocode,
                int(ew_start) if ew_start else None,
                int(ew_end) if ew_end else None,
            ).rename(
                columns={
                    "SE": "epidemiological_week",
                    "data_iniSE": "epidemiological_week_start_date",
                    "municipio_geocodigo": "municipality_geocode",
                    "casos": "cases",
                    "nivel": "alert_level",
                }
            )
        except (KeyError, ValueError) as exc:
            return Response(
                build_error_response(str(exc), code="invalid_query"),
                status=400,
            )

        return Response(
            build_success_response(normalize_alert_city_records(records))
        )


class PublicEpiYearWeekView(APIView):
    """Return a normalized epidemiological year/week response."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            epidate = datetime.strptime(
                request.query_params["epidate"], "%Y-%m-%d"
            )
        except (KeyError, ValueError) as exc:
            return Response(
                build_error_response(str(exc), code="invalid_query"),
                status=400,
            )

        year_week = episem(epidate, sep="")
        return Response(
            build_success_response(
                {
                    "epidemiological_week": year_week,
                    "epidemiological_year": year_week[:4],
                    "epidemiological_week_number": year_week[4:],
                }
            )
        )


class PublicNotificationReducedCSVView(NotificationReducedCSV_View):
    """Preserve the existing public CSV response behavior under v1."""

    permission_classes = [AllowAny]
