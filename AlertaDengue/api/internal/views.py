from datetime import date
from typing import Any

from django.db import DatabaseError
from pydantic import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.internal.historical_alerts import (
    HistoricalAlertFilters,
    get_historical_alert_queryset,
    get_historical_alert_response_fields,
    serialize_historical_alert,
)
from api.internal.permissions import HasNotificationAPIAccess
from api.internal.services import list_notifications


class NotificationListView(APIView):
    permission_classes = [HasNotificationAPIAccess]

    def get(self, request):
        try:
            payload = list_notifications(request.query_params)
        except ValidationError as exc:
            return Response({"detail": exc.errors()}, status=400)
        except DatabaseError:
            return Response(
                {"detail": "Database error while listing notifications."},
                status=500,
            )

        return Response(payload)


class HistoricalAlertListView(APIView):
    """Return bounded, normalized historical-alert records."""

    permission_classes = [AllowAny]
    _INTEGER_PARAMS = (
        "municipality_geocode",
        "epidemiological_week",
        "start_week",
        "end_week",
        "alert_level",
        "limit",
        "offset",
    )
    _DATE_PARAMS = ("start_date", "end_date")

    def get(self, request):
        try:
            disease = request.query_params.get("disease")
            if not disease:
                raise ValueError("disease is required")

            query_params = self._parse_query_params(request.query_params)
            filters = HistoricalAlertFilters(disease, **query_params)
            queryset = get_historical_alert_queryset(
                filters.disease,
                **query_params,
            )
            results = [
                self._serialize_record(record, filters.disease)
                for record in queryset
            ]
        except (TypeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response({"count": len(results), "results": results})

    @classmethod
    def _parse_query_params(cls, query_params):
        """Convert supported string parameters to service-layer types."""
        parsed: dict[str, Any] = {}
        for parameter in cls._INTEGER_PARAMS:
            if parameter in query_params:
                parsed[parameter] = int(query_params[parameter])
        for parameter in cls._DATE_PARAMS:
            if parameter in query_params:
                parsed[parameter] = date.fromisoformat(query_params[parameter])
        if "ordering" in query_params:
            parsed["ordering"] = query_params["ordering"]
        return parsed

    @staticmethod
    def _serialize_record(record, disease):
        """Serialize one record using only service-declared response fields."""
        serialized = serialize_historical_alert(record, disease)
        return {
            field: serialized[field]
            for field in get_historical_alert_response_fields()
        }
