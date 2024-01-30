import json
from datetime import datetime

from dados.episem import episem
from django.http import HttpResponse
from django.views.generic.base import View

# local
from .db import STATE_NAME, AlertCity

class _GetMethod:
    """"""

    def _get(self, param, default=None, cast=None, error_message=None):
        """

        :param param:
        :param default:
        :return:
        """
        if (
            error_message is not None
            and param not in self.request.GET
            and default is None
        ):
            raise Exception(error_message)

        result = (
            self.request.GET[param] if param in self.request.GET else default
        )

        return result if cast is None or result is None else cast(result)

class AlertCityView(View, _GetMethod):
    """ """

    request = None

    def get(self, request):
        self.request = request
        format = ""

        try:
            disease = self._get(
                "disease", error_message="Disease sent is empty."
            ).lower()
            geocode = self._get(
                "geocode", cast=int, error_message="GEO-Code sent is empty."
            )
            format = self._get(
                "format", error_message="Format sent is empty."
            ).lower()
            ew_start = self._get(
                "ew_start",
                default=True,
                cast=int,
                error_message="Epidemic start week sent is empty.",
            )
            ew_end = self._get(
                "ew_end",
                default=True,
                cast=int,
                error_message="Epidemic end week sent is empty.",
            )
            ey_start = self._get(
                "ey_start",
                default=True,
                cast=int,
                error_message="Epidemic start year sent is empty.",
            )

            ey_end = self._get(
                "ey_end",
                default=True,
                cast=int,
                error_message="Epidemic end year sent is empty.",
            )

            if format not in ["csv", "json"]:
                raise Exception(
                    "The output format available are: `csv` or `json`."
                )

            eyw_start = ey_start * 100 + ew_start
            eyw_end = ey_end * 100 + ew_end

            if self._get("ew_end"):
                # Use the keyword arguments for infodengue website
                df = AlertCity.search(
                    geocode=geocode,
                    disease=disease,
                    ew_start=eyw_start,
                    ew_end=eyw_end,
                ).execute()
            else:
                # Use the keyword arguments for mobile app
                df = AlertCity.search(
                    geocode=geocode,
                    disease=disease,
                ).execute()

            df.drop(
                columns=["municipio_geocodigo", "municipio_nome"],
                inplace=True,
            )

            if format == "json":
                result = df.to_json(orient="records")
            else:
                result = df.to_csv(index=False)
        except Exception as e:
            if format == "json":
                result = '{"error_message": "%s"}' % e
            else:
                result = "[EE] error_message: %s" % e

        content_type = "application/json" if format == "json" else "text/plain"
        response = HttpResponse(result, content_type=content_type)

        if format == "csv":
            response["Content-Disposition"] = (
                "attachment;"
                f' filename="{disease}_{ew_start}-{ew_end}.{format}"'
            )

        return response


class EpiYearWeekView(View, _GetMethod):
    """
    JSON output
    """

    request = None

    def get(self, request):
        self.request = request
        output_format = "json"

        try:
            epidate_s = self._get(
                "epidate", error_message="epidate sent is empty."
            )

            epidate = datetime.strptime(epidate_s, "%Y-%m-%d")
            epi_year_week = episem(epidate, sep="")

            if output_format == "json":
                result = json.dumps(
                    dict(
                        epi_year_week=epi_year_week,
                        epi_year=epi_year_week[:4],
                        epi_week=epi_year_week[4:],
                    )
                )
            else:
                result = "" % epi_year_week

        except Exception as e:
            if output_format == "json":
                result = '{"error_message": "%s"}' % e
            else:
                result = "[EE] error_message: %s" % e

        content_type = (
            "application/json" if output_format == "json" else "text/plain"
        )

        return HttpResponse(result, content_type=content_type)
