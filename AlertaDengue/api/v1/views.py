"""Views for the public REST API v1 surface."""

from datetime import datetime

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.responses import build_error_response, build_success_response
from api.v1.services import get_public_alert_city_records
from api.views import NotificationReducedCSV_View
from dados.episem import episem


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
    """Return normalized city-alert records through historical-alert ORM."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            disease = request.query_params["disease"].lower()
            geocode = int(request.query_params["geocode"])
            ew_start = request.query_params.get("ew_start")
            ew_end = request.query_params.get("ew_end")
            records = get_public_alert_city_records(
                disease=disease,
                geocode=geocode,
                ew_start=int(ew_start) if ew_start else None,
                ew_end=int(ew_end) if ew_end else None,
            )
        except (KeyError, ValueError) as exc:
            return Response(
                build_error_response(str(exc), code="invalid_query"),
                status=400,
            )

        return Response(build_success_response(records))


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
