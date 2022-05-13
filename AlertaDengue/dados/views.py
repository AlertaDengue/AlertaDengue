import datetime
import json
import locale
import os
import random
from collections import OrderedDict, defaultdict
from copy import deepcopy
from pathlib import Path, PurePath
from time import mktime
from typing import Dict, List, Tuple

import fiona
import geojson
import numpy as np
import pandas as pd
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles.finders import find
from django.http import HttpResponse
from django.shortcuts import redirect
from django.templatetags.static import static
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView, View
from gis.geotiff import convert_from_shapefile

# local
from . import dbdata
from . import models as M
from .charts.alerts import AlertCitiesCharts
from .charts.cities import ReportCityCharts
from .charts.home import (
    _create_indicator_chart,
    _create_scatter_chart,
    _create_stack_chart,
)
from .charts.states import ReportStateCharts
from .dbdata import (
    ALERT_COLOR,
    CID10,
    MRJ_GEOCODE,
    STATE_INITIAL,
    STATE_NAME,
    Forecast,
    RegionalParameters,
    ReportCity,
    ReportState,
    data_hist_uf,
)
from .episem import episem, episem2date
from .maps import get_city_info
from .models import City


def get_static(static_dir):
    if not settings.DEBUG:
        return Path(static(static_dir))
    _app_dir = settings.APPS_DIR
    path_to_find = PurePath(find(static_dir))
    return str(path_to_find.relative_to(_app_dir))


DBF = apps.get_model("dbf", "DBF")

locale.setlocale(locale.LC_TIME, locale="pt_BR.UTF-8")


dados_alerta = dbdata.get_alerta_mrj()
dados_alerta_chik = dbdata.get_alerta_mrj_chik()
dados_alerta_zika = dbdata.get_alerta_mrj_zika()

with open(os.path.join(settings.STATICFILES_DIRS[0], "rio_aps.geojson")) as f:
    polygons = geojson.load(f)


def _get_disease_label(disease_code: str) -> str:
    return (
        "Dengue"
        if disease_code == "dengue"
        else "Chikungunya"
        if disease_code == "chikungunya"
        else "Zika"
        if disease_code == "zika"
        else None
    )


def hex_to_rgb(value):
    value = value.lstrip("#")
    lv = len(value)
    return tuple(
        int(value[i : i + lv // 3], 16)
        for i in range(0, lv, lv // 3)  # noqa: E203
    )


def get_last_color_alert(geocode, disease, color_type="rgb"):
    """
    :param geocode:
    :param disease:
    :param color_type: rba|hex
    :return:
    """
    df_level = dbdata.get_last_alert(geocode, disease)

    level = (
        0
        if df_level.empty
        else 0
        if not (1 <= df_level.nivel[0] <= 4)
        else df_level.nivel[0]
    )

    color_list = [
        "#cccccc",  # gray
        "#00ff00",  # green
        "#ffff00",  # yellow
        "#ff9900",  # orange
        "#ff0000",  # red
    ]

    if color_type == "hex":
        return color_list[level]

    return hex_to_rgb(color_list[level])


def get_alert(disease="dengue"):
    """
    Read the data and return the alert status of all APs.
    returns a tuple with the following elements:
    - alert: dictionary with the alert status per AP
    - current: tuple with all variables from the last SE
    - case_series: dictionary with 12-weeks case series per AP
    - last_year: integer representing the total number of cases 52 weeks ago.
    - obs_case_series
    - min_max_est
    :rtype : tuple
    """
    # dados_alerta and dados_alert_chick are global variables
    df = (
        dados_alerta
        if disease == "dengue"
        else dados_alerta_chik
        if disease == "chikungunya"
        else dados_alerta_zika
        if disease == "zika"
        else None
    )

    if df is None:
        raise Exception("Doença não cadastrada.")

    df = df.copy()
    df.fillna(0, inplace=True)

    last_SE = df.se.max()  # Last epidemiological week
    current = df[df["se"] == last_SE]  # Current status

    G = df.groupby("aps")
    alert = defaultdict(lambda: 0)
    case_series = {}  # estimated
    obs_case_series = {}
    min_max_est = {}
    last_year = None

    for ap in G.groups.keys():
        # .tail()  # only calculates on the series tail
        adf = G.get_group(ap).sort_values("data")

        k = str(float(ap.split("AP")[-1]))

        case_series[k] = [int(v) for v in adf.casos_est.iloc[-12:].values]
        obs_case_series[k] = [int(v) for v in adf.casos.iloc[-12:].values]
        alert[ap] = adf.nivel.iloc[-1]
        last_year = int(adf.casos.iloc[-52])
        min_max_est[ap] = (
            adf.casos_estmin.iloc[-1],
            adf.casos_estmax.iloc[-1],
        )

    return alert, current, case_series, last_year, obs_case_series, min_max_est


def get_municipio(request):
    q = request.GET["q"]
    muns = dbdata.get_city(q)
    data = json.dumps(
        [{"geocodigo": g, "nome": n, "uf": u} for g, n, u in muns]
    )
    return HttpResponse(data, content_type="application/json")


def load_series():
    """
    Monta as séries para visualização no site
    """
    series = defaultdict(lambda: defaultdict(lambda: []))
    G = dados_alerta.groupby("aps")
    for ap in G.groups.keys():
        series[ap]["dia"] = [
            int(mktime(datetime.datetime.strptime(d, "%Y-%m-%d").timetuple()))
            if isinstance(d, str)
            else None
            for d in G.get_group(ap).data
        ]
        series[ap]["tweets"] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).tweets
        ]
        series[ap]["tmin"] = [
            float(i) if not np.isnan(i) else None for i in G.get_group(ap).tmin
        ]
        series[ap]["casos_est"] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).casos_est
        ]
        series[ap]["casos"] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).casos
        ]
        series[ap]["alerta"] = [
            c - 1 if not np.isnan(c) else None for c in G.get_group(ap).cor
        ]
    return series


class _GetMethod:
    """"""

    def _get(self, param, default=None):
        """
        :param param:
        :param default:
        :return:
        """
        result = (
            self.request.GET[param] if param in self.request.GET else default
        )

        return result if result else default


class AboutPageView(TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super(AboutPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class TeamPageView(TemplateView):
    template_name = "team.html"

    def get_context_data(self, **kwargs):
        context = super(TeamPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class JoininPageView(TemplateView):
    template_name = "joinin.html"

    def get_context_data(self, **kwargs):
        context = super(JoininPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class DataPublicServicesPageView(TemplateView):
    template_name = "services.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        service = kwargs.get("service", None)
        service_type = (
            None if "service_type" not in kwargs else kwargs["service_type"]
        )

        if service == "maps":
            if service_type is None:

                geo_info_path = get_static("geojson/geo_info.json")

                with open(geo_info_path) as f:
                    geo_info_json = json.load(f)

                    context.update(
                        {
                            "geocodes": sorted(list(geo_info_json.keys())),
                            "mapserver_url": settings.MAPSERVER_URL,
                            "geo_info": geo_info_json,
                        }
                    )
                self.template_name = "services_maps.html"
            else:
                self.template_name = "services_maps_doc.html"
        elif service == "tutorial":
            if service_type is None:
                self.template_name = "services_tutorial.html"
            elif service_type == "R":
                self.template_name = "services_tutorial_R.html"
            else:
                self.template_name = "services_tutorial_Python.html"
        elif service == "api":
            if service_type is None:
                self.template_name = "services_api.html"

                options_cities = ""
                for state_abbv, state_name in STATE_NAME.items():
                    for (geocode, city_name,) in RegionalParameters.get_cities(
                        state_name=state_name
                    ).items():
                        options_cities += """
                        <option value="{0!s}">
                            {0!s} - {1!s} - {2!s}
                        </option>""".format(
                            geocode, city_name.upper(), state_abbv
                        )

                dt_end = datetime.datetime.now()
                dt_start = dt_end - datetime.timedelta(weeks=4)

                yw_start = episem(dt_start, sep="")
                yw_end = episem(dt_end, sep="")

                dt_start_fmt = episem2date(yw_start, 1).strftime("%Y-%m-%d")
                dt_end_fmt = episem2date(yw_end, 1).strftime("%Y-%m-%d")

                context.update(
                    {
                        "options_cities": options_cities,
                        "date_query_start": dt_start_fmt,
                        "date_query_end": dt_end_fmt,
                    }
                )

                return context
            elif service_type == "tutorialR":
                self.template_name = "services_api_tutorialR.html"
            else:
                self.template_name = "services_api_doc.html"
        else:
            self.template_name = "services.html"

        return context


class AlertaMainView(TemplateView):
    template_name = "main.html"

    def get_context_data(self, **kwargs):
        context = super(AlertaMainView, self).get_context_data(**kwargs)

        return context


class AlertCityPageBaseView(TemplateView, _GetMethod):
    pass


class AlertaMRJPageView(AlertCityPageBaseView):
    """
    Rio de Janeiro Alert View
    """

    template_name = "alerta_mrj.html"

    def get_context_data(self, **kwargs):
        context = super(AlertaMRJPageView, self).get_context_data(**kwargs)

        chart_alerts = AlertCitiesCharts()

        disease_code = context["disease"]

        disease_label = _get_disease_label(disease_code)

        bairros_mrj = {
            1.0: "AP 1: Centro e adjacências",
            2.1: "AP 2.1: Zona Sul",
            2.2: "AP 2.2: Tijuca e adjacências",
            3.1: "AP 3.1: Bonsucesso e adjacências",
            3.2: "AP 3.2: Meier e adjacências",
            3.3: "AP 3.3: Madureira e adjacências",
            4.0: "AP 4: Barra, Recreio e Jacarepaguá",
            5.1: "AP 5.1: Bangu e adjacências",
            5.2: "AP 5.2: Campo Grande e adjacências",
            5.3: "AP 5.3: Santa Cruz e adjacências",
        }

        geocode = str(MRJ_GEOCODE)

        city_info = get_city_info(geocode)

        # forecast epiweek reference
        forecast_date_min, forecast_date_max = Forecast.get_min_max_date(
            geocode=geocode, cid10=CID10[disease_code]
        )

        forecast_date_ref = self._get("ref", forecast_date_max)

        if forecast_date_ref is None:
            epiweek = None
        else:
            epiweek = episem(forecast_date_ref).replace("W", "")

        (
            alert,
            current,
            case_series,
            last_year,
            observed_cases,
            min_max_est,
        ) = get_alert(disease_code)

        if alert:
            casos_ap = {}
            alerta = {}

            for ap, v in alert.items():
                if ap not in current.aps:
                    continue

                _ap = float(ap.split("AP")[-1])

                mask = current.aps == ap
                _v = int(current[mask]["casos_est"].values.astype(int)[0])

                casos_ap.update({_ap: _v})
                alerta.update({_ap: int(v) - 1})

            semana = str(current.se.iat[-1])[-2:]
            segunda = current.data.iat[-1]
            # estimated cases
            total_series = sum(
                np.array(list(case_series.values())), np.zeros(12, int)
            )
            # observed cases
            total_observed_series = sum(
                np.array(list(observed_cases.values())), np.zeros(12, int)
            )
        else:
            casos_ap = {}
            alerta = {}
            semana = 0
            segunda = datetime.datetime.now() - datetime.timedelta(7)
            total_series = [0]
            total_observed_series = [0]

        try:
            city_chart = chart_alerts.create_alert_chart(
                geocode,
                city_info["nome"],
                disease_label,
                disease_code,
                epiweek,
            )
        except ValueError:
            context = {
                "message": _(
                    "A doença {} não está registrada "
                    "em nosso banco de dados para o município de {}."
                ).format(disease_label, city_info["nome"])
            }
            self.template_name = "error.html"
            return context

        context.update(
            {
                "geocodigo": geocode,  # legacy
                "geocode": geocode,
                "state_abv": "RJ",
                "state": city_info["uf"],
                "nome": city_info["nome"],
                "populacao": city_info["populacao"],
                "incidencia": (
                    total_observed_series[-1] / city_info["populacao"]
                )
                * 100000,  # casos/100000
                "casos_por_ap": json.dumps(casos_ap),
                "alerta": alerta,
                "novos_casos": sum(casos_ap.values()),
                "bairros": bairros_mrj,
                "min_est": sum(i[0] for i in min_max_est.values()),
                # 'min_est': sum(current.casos_estmin.values),
                "max_est": sum(i[1] for i in min_max_est.values()),
                # 'max_est': sum(current.casos_estmax.values),
                "series_casos": case_series,
                "SE": int(semana),
                "WEEK": str(semana),
                "yearweek": str(current.se.iat[0])[:],
                "data1": segunda.strftime("%d de %B de %Y"),
                "data2": (
                    segunda + datetime.timedelta(6)
                ),  # .strftime("%d de %B de %Y")
                "last_year": last_year,
                "look_back": len(total_series),
                "total_series": ", ".join(map(str, total_series)),
                "total_observed": total_observed_series[-1],
                "total_observed_series": ", ".join(
                    map(str, total_observed_series)
                ),
                "disease_label": disease_label,
                "disease_code": disease_code,
                "forecast_date_ref": forecast_date_ref,
                "forecast_date_min": forecast_date_min,
                "forecast_date_max": forecast_date_max,
                "epiweek": epiweek,
                "geojson_url": "/static/rio_aps.geojson",
                "chart_alert": city_chart,
            }
        )
        return context


class AlertaMunicipioPageView(AlertCityPageBaseView):
    template_name = "alerta_municipio.html"

    def dispatch(self, request, *args, **kwargs):
        super(AlertaMunicipioPageView, self).get_context_data(**kwargs)

        geocode = kwargs["geocodigo"]

        if int(geocode) == MRJ_GEOCODE:  # Rio de Janeiro
            return redirect("dados:mrj", disease="dengue", permanent=True)

        return super(AlertaMunicipioPageView, self).dispatch(
            request, *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = super(AlertaMunicipioPageView, self).get_context_data(
            **kwargs
        )

        chart_alerts = AlertCitiesCharts()

        disease_code = context["disease"]

        disease_label = _get_disease_label(disease_code)

        geocode = context["geocodigo"]

        city_info = get_city_info(geocode)

        # forecast epiweek reference
        forecast_date_min, forecast_date_max = Forecast.get_min_max_date(
            geocode=geocode, cid10=CID10[disease_code]
        )

        forecast_date_ref = self._get("ref", forecast_date_max)

        if forecast_date_ref is None:
            epiweek = None
        else:
            epiweek = episem(forecast_date_ref).replace("W", "")

        (
            alert,
            SE,
            case_series,
            last_year,
            observed_cases,
            min_max_est,
            dia,
            prt1,
        ) = dbdata.get_city_alert(geocode, disease_code)

        if alert is not None:
            casos_ap = {geocode: int(case_series[-1])}
            bairros = {geocode: city_info["nome"]}
            total_series = case_series[-12:]
            total_observed_series = observed_cases[-12:]
        else:
            casos_ap = {}
            bairros = {}
            total_series = [0]
            total_observed_series = [0]

        try:
            city_chart = chart_alerts.create_alert_chart(
                geocode,
                city_info["nome"],
                disease_label,
                disease_code,
                epiweek,
            )
        except ValueError:
            context = {
                "message": _(
                    "A doença {} não está registrada "
                    "em nosso banco de dados para o município de {}."
                ).format(disease_label, city_info["nome"])
            }
            self.template_name = "error.html"
            return context

        context.update(
            {
                "geocodigo": geocode,  # legacy
                "geocode": geocode,
                "state": city_info["uf"],
                "state_abv": STATE_INITIAL[city_info["uf"]],
                "nome": city_info["nome"],
                "populacao": city_info["populacao"],
                "incidencia": (case_series[-1] / city_info["populacao"])
                * 100000,  # casos/100000
                "casos_por_ap": json.dumps(casos_ap),
                "alerta": {geocode: alert},
                "prt1": prt1 * 100,
                "novos_casos": case_series[-1],
                "bairros": bairros,
                "min_est": min_max_est[0],
                "max_est": min_max_est[1],
                "series_casos": {geocode: case_series[-12:]},
                "SE": SE,
                "WEEK": str(SE)[4:],
                "data1": dia.strftime("%d de %B de %Y"),
                # .strftime("%d de %B de %Y")
                "data2": (dia + datetime.timedelta(6)),
                "last_year": last_year,
                "look_back": len(total_series),
                "total_series": ", ".join(map(str, total_series)),
                "total_observed": total_observed_series[-1],
                "total_observed_series": ", ".join(
                    map(str, total_observed_series)
                ),
                "disease_label": disease_label,
                "disease_code": disease_code,
                "forecast_date_ref": forecast_date_ref,
                "forecast_date_min": forecast_date_min,
                "forecast_date_max": forecast_date_max,
                "epiweek": epiweek,
                "geojson_url": "/static/geojson/%s.json" % geocode,
                "chart_alert": city_chart,
            }
        )
        return context


class AlertaGeoJSONView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(geojson.dumps(polygons))


class DetailsPageView(TemplateView):
    template_name = "details.html"

    def get_context_data(self, **kwargs):
        context = super(DetailsPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        series = load_series()
        aps = list(series.keys())
        aps.sort()
        ga = {}
        ya = {}
        oa = {}
        ra = {}
        for k, v in series.items():
            ga[k] = [1 if a == 0 else None for a in v["alerta"]]
            ya[k] = [1 if a == 1 else None for a in v["alerta"]]
            oa[k] = [1 if a == 2 else None for a in v["alerta"]]
            ra[k] = [1 if a == 3 else None for a in v["alerta"]]

        context.update(
            {
                "APS": aps,
                "green_alert": json.dumps(ga),
                "yellow_alert": json.dumps(ya),
                "casos": json.dumps(series),
                "red_alert": json.dumps(ra),
                "orange_alert": json.dumps(oa),
                "xvalues": series["AP1"]["dia"],
            }
        )
        return context


class SinanCasesView(View):
    def get(self, request, year, sample):
        sample = int(sample)
        try:
            assert int(year) in [2010, 2011, 2012, 2013]
        except AssertionError:
            messages.error(
                self.request,
                "O projeto conté dados apenas dos anos 2010 a 2013.",
            )

        sample = 1 if sample == 0 else sample / 100.0
        cases = '{"type":"FeatureCollection", "features":['
        if int(year) == 2010:
            dados = M.Dengue_2010.objects.geojson()
        elif int(year) == 2011:
            dados = M.Dengue_2011.objects.geojson()
        elif int(year) == 2012:
            dados = M.Dengue_2012.objects.geojson()
        elif int(year) == 2013:
            dados = M.Dengue_2013.objects.geojson()
        else:
            dados = []

        if len(dados) < 5500:
            sample = 1
        for c in random.sample(list(dados), int(len(dados) * sample)):
            cases += (
                '{"type":"Feature","geometry":'
                + c.geojson
                + ', "properties":{"data":"'
                + c.dt_notific.isoformat()
                + '"}},'
            )
        cases = cases[:-1] + "]}"
        # json.loads(cases)
        return HttpResponse(cases, content_type="application/json")


class AlertaStateView(TemplateView):
    template_name = "state_cities.html"

    _state_name = STATE_NAME

    def get_context_data(self, **kwargs):
        """
        :param kwargs:
        :return:
        """
        context = super(AlertaStateView, self).get_context_data(**kwargs)

        series_data_rj = None

        cities_alert = dbdata.NotificationResume.get_cities_alert_by_state(
            self._state_name[context["state"]], context["disease"]
        )

        alerts = dict(
            cities_alert[["municipio_geocodigo", "level_alert"]].values
        )

        mun_dict = dict(cities_alert[["municipio_geocodigo", "nome"]].values)
        is_just_rj = False

        if (
            not mun_dict
            and context["state"] == "RJ"
            and context["disease"] == "chikungunya"
        ):
            geo_id_rj = MRJ_GEOCODE
            mun_dict = {geo_id_rj: "Rio de Janeiro"}
            series_data_rj = dbdata.load_series(geo_id_rj, "chikungunya")[
                str(MRJ_GEOCODE)
            ]
            alerts = {str(geo_id_rj): series_data_rj["alerta"][-1]}
            is_just_rj = True

        mun_dict_ordered = OrderedDict(
            sorted(mun_dict.items(), key=lambda v: v[1])
        )

        geo_ids = list(mun_dict.keys())

        dbf = (
            DBF.objects.filter(abbreviation=context["state"])
            .order_by("export_date")
            .last()
        )

        if dbf is None:
            last_update = _("desconhecida")
        else:
            last_update = dbf.export_date

        if len(geo_ids) > 0:
            if not is_just_rj:
                cases_series_last_12 = dbdata.NotificationResume.tail_estimated_cases(  # noqa: E501
                    geo_ids, 12
                )
            else:
                cases_series_last_12 = {geo_id_rj: series_data_rj["casos_est"]}
        else:
            cases_series_last_12 = {}

        context.update(
            {
                "state_abv": context["state"],
                "state": self._state_name[context["state"]],
                "map_center": dbdata.MAP_CENTER[context["state"]],
                "map_zoom": dbdata.MAP_ZOOM[context["state"]],
                "mun_dict": mun_dict,
                "mun_dict_ordered": mun_dict_ordered,
                "geo_ids": geo_ids,
                "alerts_level": alerts,
                # estimated cases is used to show a chart of the last 12 events
                "case_series": cases_series_last_12,
                "disease_label": context["disease"].title(),
                "last_update": last_update,
            }
        )
        return context


class ChartsMainView(TemplateView):
    template_name = "components/home/charts.html"

    def get_img_map(self, state_abbv: str, disease: str) -> str:

        """
        Verify if file exists and return a string to path.
        Parameters
        ----------
        state_abbv: str
            State full name
        disease: str
            option: dengue|chikungunya|zika
        Returns
        -------
        image_path: str
        """

        img_name = Path(
            "img",
            "incidence_maps",
            "state",
            f"incidence_{state_abbv}_{disease}.png",
        )

        img_data = f"""
            <div class='mt-4'>
                <img
                src='{get_static(img_name)}'
                alt=''
                title='Mapa de {disease} para o estado de {state_abbv}'
                style='width:100%'
                />
            </div>"""

        return img_data

    def get_context_data(self, **kwargs):
        context = super(ChartsMainView, self).get_context_data(**kwargs)

        create_scatter_chart = defaultdict(dict)
        create_indicator_chart = defaultdict(dict)
        create_stack_chart = defaultdict(dict)
        count_cities = defaultdict(dict)
        create_maps = defaultdict(dict)
        last_se = defaultdict(dict)
        empty_charts_count = defaultdict(dict)
        states_alert = defaultdict(dict)
        notif_resume = dbdata.NotificationResume

        state_abbv = context["state"]
        state_name = STATE_NAME.get(state_abbv)
        states_alert[state_abbv] = state_abbv

        # Use as an argument to fetch in database
        for disease in tuple(dbdata.DISEASES_NAMES):
            no_data_chart = f"""
                <div class='alert alert-primary' align='center'>
                    Não há dados suficientes para a geração do
                    gráfico sobre {disease}
                </div>"""

            empty_charts_count[disease] = 0

            create_maps[disease][state_abbv] = self.get_img_map(
                state_abbv, disease
            )

            # count_cities_by_uf('Santa Catarina', 'dengue')
            count_cities[disease][
                state_abbv
            ] = notif_resume.count_cities_by_uf(state_name, disease)

            df = data_hist_uf(state_abbv=state_abbv, disease=disease)

            if disease == "dengue":
                if not df.empty:
                    last_se[state_abbv] = (
                        str(df.SE.max())[4:] + "/" + str(df.SE.max())[:4]
                    )

                else:
                    last_se[state_abbv] = ""

            # scatterchart
            if df.casos_est.any():
                df_cases = deepcopy(df)

                keys = ["casos_est", "casos"]
                df_by_uf = df_cases.groupby(["SE"])[keys].sum()

                scatter_chart = _create_scatter_chart(df=df_by_uf)
            else:
                scatter_chart = no_data_chart
                empty_charts_count[disease] += 1

            create_scatter_chart[disease][state_abbv] = scatter_chart

            # indicatorchart
            if df.casos.any():
                df_receptivity = deepcopy(df)

                indicator_chart = _create_indicator_chart(
                    df=df_receptivity, state_abbv=state_abbv
                )
            else:
                indicator_chart = no_data_chart
                empty_charts_count[disease] += 1

            create_indicator_chart[disease][state_abbv] = indicator_chart

            # stackbarchart
            df_nivel = deepcopy(df)

            if not df_nivel.empty:
                df_alert = (
                    df_nivel.groupby(["SE", "nivel"])["municipio_geocodigo"]
                    .count()
                    .reset_index()
                )

                color_alert = {1: "Green", 2: "Yellow", 3: "Orange", 4: "Red"}
                df_alert.nivel = df_alert.nivel.apply(
                    lambda v: f"{color_alert[v]} Alert"
                )

                this_year_week = df_alert.SE.max()
                get_week = df_alert.SE >= this_year_week - 53
                df_alert_uf = df_alert[get_week].sort_values(
                    by=["nivel"], ascending=False
                )

                stack_chart = _create_stack_chart(
                    df=df_alert_uf,
                )
            else:
                stack_chart = no_data_chart
                empty_charts_count[disease] += 1

            create_stack_chart[disease][state_abbv] = stack_chart

        context.update(
            {
                "chart_scatter": create_scatter_chart,
                "chart_indicator": create_indicator_chart,
                "chart_stack": create_stack_chart,
                "count_cities": count_cities,
                "last_se": last_se,
                "create_maps": create_maps,
                "no_data_chart": no_data_chart,
                "empty_charts_count": empty_charts_count,
                "states_alert": states_alert,
            }
        )
        return context


class GeoTiffView(View):
    def get(self, request, geocodigo, disease):
        """
        :param kwargs:
        :return:
        """
        geocode = geocodigo

        # load shapefile
        for path in (settings.STATIC_ROOT, settings.STATICFILES_DIRS[0]):
            if not os.path.isdir(path):
                continue
            shp_path = os.path.join(path, "shapefile")

        shp = fiona.open(os.path.join(shp_path, "%s.shp" % geocode))

        result = convert_from_shapefile(
            shapefile=shp, rgb_color=get_last_color_alert(geocode, disease)
        )

        response = HttpResponse(
            result, content_type="application/force-download"
        )

        response["Content-Disposition"] = (
            "attachment; filename=%s.tiff" % geocode
        )

        return response


class GeoJsonView(View):
    """"""

    def get(self, request, geocodigo, disease):
        """
        :param kwargs:
        :return:
        """
        geocode = geocodigo

        # load shapefile
        for path in (settings.STATIC_ROOT, settings.STATICFILES_DIRS[0]):
            if not os.path.isdir(path):
                continue
            geojson_path = os.path.join(path, "geojson", "%s.json" % geocode)

        hex_color = get_last_color_alert(geocode, disease, color_type="hex")

        with open(geojson_path) as f:
            geojson_data = geojson.load(f)

        geojson_data["features"][0]["properties"]["fill"] = hex_color
        result = geojson.dumps(geojson_data)

        response = HttpResponse(
            result, content_type="application/force-download"
        )

        response["Content-Disposition"] = (
            "attachment; filename=%s.json" % geocode
        )

        return response


class ReportView(TemplateView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        :param kwargs:
        :return:
        """
        context = super().get_context_data(**kwargs)

        report_type = (
            context["report_type"] if "report_type" in context else None
        )

        if report_type is None:
            context.update(self.view_filter_report_type(context))
        elif report_type == "city":
            context.update(self.view_filter_city(context))
        else:
            context.update(self.view_filter_state(context))

        context.update({"disease_list": CID10})

        return context

    def view_filter_report_type(self, context):
        """
        :param context:
        :return:
        """
        self.template_name = "report_filter_report_type.html"

        options_states = ""
        for state_initial, state_name in STATE_NAME.items():
            options_states += """
            <option value="%(state_initial)s">
                %(state_name)s
            </option>""" % {
                "state_name": state_name,
                "state_initial": state_initial,
            }

        context.update({"options_states": options_states})

        return context

    def view_filter_city(self, context):
        """
        :param context:
        :return:
        """
        self.template_name = "report_filter_city.html"

        options_cities = ""
        for geocode, city_name in RegionalParameters.get_cities(
            state_name=STATE_NAME[context["state"]]
        ).items():
            options_cities += """
            <option value="%(geocode)s">
                %(city_name)s
            </option>""" % {
                "geocode": geocode,
                "city_name": city_name,
            }

        dt = datetime.datetime.now() - datetime.timedelta(days=7)
        yw = episem(dt, sep="")
        dt_fmt = episem2date(yw, 1).strftime("%Y-%m-%d")

        context.update(
            {"options_cities": options_cities, "date_query": dt_fmt}
        )

        return context

    def view_filter_state(self, context):
        """
        :param context:
        :return:
        """
        self.template_name = "report_filter_state.html"

        dt = datetime.datetime.now() - datetime.timedelta(days=7)
        yw = episem(dt, sep="")
        dt_fmt = episem2date(yw, 1).strftime("%Y-%m-%d")

        context.update({"date_query": dt_fmt})

        return context


class ReportCityView(TemplateView):
    template_name = "report_city.html"

    def raise_error(self, context, message):
        """
        :return:
        """
        self.template_name = "error.html"
        context.update({"message": message})
        return context

    def get_context_data(self, **kwargs):
        """
        :param kwargs:
        :return:
        """
        context = super(ReportCityView, self).get_context_data(**kwargs)

        geocode = int(context["geocode"])
        year_week = int(context["year_week"])
        year, week = context["year_week"][:4], context["year_week"][-2:]

        error_message_city_doesnt_exist = (
            "Esse municipio não participa do Infodengue. Se tiver "
            + "interesse em aderir, contacte-nos pelo email "
            + ' <a href="mailto:alerta_dengue@fiocruz.br">'
            + "alerta_dengue@fiocruz.br</a>"
        )

        city = City.objects.get(pk=int(geocode))

        regional_get_param = RegionalParameters.get_station_data(
            geocode=int(geocode), disease="dengue"
        )[0]

        # TODO: Fix NA's in the parameters table
        if regional_get_param[5] == "NA":
            regional_get_param[5] = 0

        threshold_pre_epidemic = regional_get_param[7]
        threshold_pos_epidemic = regional_get_param[8]
        threshold_epidemic = regional_get_param[9]

        tweet_max = 0

        # Create the dictionary with climate variables

        varcli_dict = {
            "temp.min": [_("°C temperatura mínima")],
            "temp.med": [_("°C temperatura média")],
            "temp.max": [_("°C temperatura máxima")],
            "umid.min": [_("% umidade mínima do ar")],
            "umid.med": [_("% umidade média do ar")],
            "umid.max": [_("% umidade máxima do ar")],
        }

        var_climate = {}
        varcli_pair = {}

        if regional_get_param[3]:
            climate_title1 = regional_get_param[3]
            climate_crit1 = regional_get_param[4]
            varcli_pair[climate_title1] = climate_crit1
            varcli_dict[regional_get_param[3].replace("_", ".")].append(
                regional_get_param[4]
            )

        if regional_get_param[5]:
            climate_title2 = regional_get_param[5]
            climate_crit2 = regional_get_param[6]
            varcli_pair[climate_title2] = climate_crit2
            varcli_dict[regional_get_param[5].replace("_", ".")].append(
                regional_get_param[6]
            )

        varcli_keys = [w.replace("_", ".") for w in list(varcli_pair.keys())]

        for v in varcli_keys:
            var_climate[v] = varcli_dict.get(v)

        df_dengue = ReportCity.read_disease_data(
            disease="dengue",
            geocode=geocode,
            year_week=year_week,
        )

        df_chik = ReportCity.read_disease_data(
            disease="chikungunya",
            geocode=geocode,
            year_week=year_week,
        )

        df_zika = ReportCity.read_disease_data(
            disease="zika",
            geocode=geocode,
            year_week=year_week,
        )

        total_n_dengue = 0
        total_n_dengue_last_year = 0
        total_n_chik = 0
        total_n_chik_last_year = 0
        total_n_zika = 0
        total_n_zika_last_year = 0

        last_year_week_l = []
        disease_last_code = []

        this_year = int(context["year_week"][:4])

        climate_cols = [
            "temp.min",
            "temp.med",
            "temp.max",
            "umid.min",
            "umid.med",
            "umid.max",
        ]

        if not df_dengue.empty:
            last_year_week_l.append(df_dengue.index.max())

            chart_dengue_climate = ReportCityCharts.create_climate_chart(
                df=df_dengue.reset_index()[["SE", *climate_cols]],
                var_climate=var_climate,
            )

            chart_dengue_incidence = ReportCityCharts.create_incidence_chart(
                df=df_dengue,
                year_week=year_week,
                threshold_pre_epidemic=threshold_pre_epidemic,
                threshold_pos_epidemic=threshold_pos_epidemic,
                threshold_epidemic=threshold_epidemic,
            )

            chart_dengue_tweets = ReportCityCharts.create_tweet_chart(
                df=df_dengue, year_week=year_week
            )
            total_n_dengue = df_dengue[df_dengue.index // 100 == this_year][
                "casos notif."
            ].sum()

            total_n_dengue_last_year = df_dengue[
                (df_dengue.index // 100 == year_week // 100 - 1)
                & (df_dengue.index <= year_week - 100)
            ]["casos notif."].sum()

            tweet_max = np.nanmax(df_dengue.tweet)

        if not df_chik.empty:
            last_year_week_l.append(df_chik.index.max())

            chart_chik_climate = ReportCityCharts.create_climate_chart(
                df=df_chik.reset_index()[["SE", *climate_cols]],
                var_climate=var_climate,
            )

            chart_chik_incidence = ReportCityCharts.create_incidence_chart(
                df=df_chik,
                year_week=year_week,
                threshold_pre_epidemic=threshold_pre_epidemic,
                threshold_pos_epidemic=threshold_pos_epidemic,
                threshold_epidemic=threshold_epidemic,
            )

            total_n_chik = df_chik[df_chik.index // 100 == this_year][
                "casos notif."
            ].sum()

            total_n_chik_last_year = df_chik[
                (df_chik.index // 100 == year_week // 100 - 1)
                & (df_chik.index <= year_week - 100)
            ]["casos notif."].sum()

        if not df_zika.empty:
            last_year_week_l.append(df_zika.index.max())

            chart_zika_climate = ReportCityCharts.create_climate_chart(
                df=df_zika.reset_index()[["SE", *climate_cols]],
                var_climate=var_climate,
            )

            chart_zika_incidence = ReportCityCharts.create_incidence_chart(
                df=df_zika,
                year_week=year_week,
                threshold_pre_epidemic=threshold_pre_epidemic,
                threshold_pos_epidemic=threshold_pos_epidemic,
                threshold_epidemic=threshold_epidemic,
            )

            total_n_zika = df_zika[df_zika.index // 100 == this_year][
                "casos notif."
            ].sum()

            total_n_zika_last_year = df_zika[
                (df_zika.index // 100 == year_week // 100 - 1)
                & (df_zika.index <= year_week - 100)
            ]["casos notif."].sum()

        if not last_year_week_l:
            return self.raise_error(context, error_message_city_doesnt_exist)

        last_year_week = int(np.nanmax(last_year_week_l))

        for df in [df_dengue, df_chik, df_zika]:
            result = df[df.index == last_year_week]
            if not result.empty:
                disease_last_code.append(float(result["level_code"]))

        max_alert_code = int(np.nanmax(disease_last_code))
        max_alert_color = ALERT_COLOR[max_alert_code]

        # param used by df.to_html
        html_param = dict(
            na_rep="",
            float_format=lambda x: ("%d" % x) if not np.isnan(x) else "",
            index=False,
            classes="table table-striped table-bordered",
        )

        cols_to_html = [
            *varcli_keys,
            "casos notif.",
            "casos_est",
            "incidência",
            # 'pr(incid. subir)',
            # 'tweet',
            "nivel",
        ]

        prepare_html = (
            lambda df: df[cols_to_html]
            .iloc[-12:, :]
            .reset_index()
            .sort_values(by="SE", ascending=[False])
            .to_html(**html_param)
        )

        last_year_week_s = str(last_year_week)
        last_year = last_year_week_s[:4]
        last_week = last_year_week_s[-2:]

        context.update(
            {
                "year": year,
                "week": week,
                "last_year": last_year,
                "last_week": last_week,
                "city_name": city.name,
                "state_name": city.state,
                "df_dengue": prepare_html(df_dengue),
                "df_chik": prepare_html(df_chik),
                "df_zika": prepare_html(df_zika),
                "chart_dengue_climate": chart_dengue_climate,
                "chart_dengue_tweets": chart_dengue_tweets,
                "chart_dengue_incidence": chart_dengue_incidence,
                "chart_chik_climate": chart_chik_climate,
                "chart_chik_incidence": chart_chik_incidence,
                "chart_zika_climate": chart_zika_climate,
                "chart_zika_incidence": chart_zika_incidence,
                "total_n_dengue": total_n_dengue,
                "total_n_dengue_last_year": total_n_dengue_last_year,
                "total_n_chik": total_n_chik,
                "total_n_chik_last_year": total_n_chik_last_year,
                "total_n_zika": total_n_zika,
                "total_n_zika_last_year": total_n_zika_last_year,
                "max_alert_color": max_alert_color.title(),
                "tweet_max": tweet_max,
            }
        )
        return context


class ReportStateView(TemplateView):
    template_name = "report_state.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def raise_error(self, context, message):
        """
        :return:
        """
        self.template_name = "error.html"
        context.update({"message": message})
        return context

    def prepare_html(self, df: pd.DataFrame, var_climate: str) -> str:
        """
        Prepare data as datafra
        Parameters
        ----------
        df : pd.DataFrame
        var_climate : str, {'umid.max', 'temp.min'}
            Climate variable
        Returns
        -------
        str
            The dataframe in HTML format.
        """
        # df['SE'] = df.index
        df.set_index("SE", drop=True, inplace=True)
        cols_to_sum = ["tweets"] + [
            "casos notif. dengue",
            "casos est. dengue",
            "casos notif. chik",
            "casos est. chik",
            "casos notif. zika",
            "casos est. zika",
        ]
        cols_to_avg = [var_climate.replace("_", ".")]

        df = df.groupby("SE")
        df = (
            df[cols_to_sum]
            .sum()
            .merge(
                df[cols_to_avg].aggregate(np.nanmean),
                how="outer",
                left_index=True,
                right_index=True,
            )
        )

        for f in cols_to_avg + cols_to_sum:
            if f not in df.columns:
                df[f] = np.nan
        df = df[cols_to_avg + cols_to_sum]

        # param used by df.to_html
        html_param = dict(
            na_rep="",
            float_format=lambda x: ("%d" % x) if not np.isnan(x) else "",
            index=False,
            classes="datatables table table-striped table-bordered",
        )

        return (
            df.iloc[-6:, :]
            .replace(0, np.nan)
            .reset_index()
            .sort_values(by="SE", ascending=[False])
            .to_html(**html_param)
        )

    def get_regional_info(
        self,
        regional_names: List[str],
        state: str,
        year_week: str,
        diseases: List[str],
    ) -> Tuple[Dict[str, Dict], str]:
        """
        Get regional information.
        Parameters
        ----------
        regional_names : List[str]
        state : str
        year_week : str
        diseases : List[str]
        Returns
        -------
        Tuple[Dict[str, Dict], str]
        """
        regional_info = {}
        last_year_week = None

        for regional_name in regional_names:
            cities = RegionalParameters.get_cities(
                state_name=STATE_NAME[state], regional_name=regional_name
            )

            station_id, var_climate = RegionalParameters.get_var_climate_info(
                cities.keys()
            )

            df = ReportState.read_disease_data(
                year_week=year_week,
                cities=cities,
                station_id=station_id,
                var_climate=var_climate,
            )

            last_year_week_ = df.SE.max()
            if last_year_week is None or last_year_week_ > last_year_week:
                last_year_week = last_year_week_

            cities_alert = {}
            chart_cases_twitter = {}

            for d in diseases:
                if not df.empty:
                    chart = ReportStateCharts.create_tweet_chart(
                        df=df, year_week=year_week, disease=d
                    )
                else:
                    chart = """
                    <br/>
                    <strong>Não há dados necessários para a geração do
                    gráfico sobre {}.
                    </strong>
                    <br/>
                    """.format(
                        d
                    )

                chart_cases_twitter[d] = chart

            # each line refers to a city
            for i, row in df[df.SE == last_year_week].iterrows():
                values = {}
                for d in diseases:
                    values.update({d: row["level_code_{}".format(d)]})
                cities_alert.update({row.geocode: values})

            regional_info.update(
                {
                    regional_name: {
                        "data": df,
                        "table": self.prepare_html(df, var_climate),
                        "cities_geocode": list(cities.keys()),
                        "cities_name": cities,
                        "cities_alert": cities_alert,
                        "chart_cases_twitter": chart_cases_twitter,
                    }
                }
            )
        return regional_info, last_year_week

    def get_alerts_info(
        self,
        diseases: List[str],
        state: str,
        last_year_week: str,
    ) -> Dict:
        """
        Return alerts information.
        Parameters
        ----------
        diseases : List[str]
        state : str
        last_year_week : str
        Returns
        -------
        dict
            The dictionary has the follow entries:
                cities_alert : Dict[str, pd.DataFrame]
                alerts : Dict[str, dict]
                mun_dict : Dict[str, dict]
                geo_ids : Dict[str, List[str]]
                cases_series_last_12 : Dict[str, Dict]
        """
        cities_alert = {}
        mun_dict = {}
        alerts = {}
        geo_ids = {}
        cases_series_last_12 = {}

        notif = dbdata.NotificationResume

        for d in diseases:
            _d = d if d != "chik" else "chikungunya"
            # check this ->
            cities_alert[d] = notif.get_cities_alert_by_state(
                state_name=STATE_NAME[state],
                disease=_d,
                epi_year_week=last_year_week,
            )

            alerts[d] = dict(
                cities_alert[d][["municipio_geocodigo", "level_alert"]].values
            )

            mun_dict[d] = dict(
                cities_alert[d][["municipio_geocodigo", "nome"]].values
            )

            geo_ids[d] = list(mun_dict[d].keys())

            if len(geo_ids[d]) > 0:
                cases_series_last_12[
                    d
                ] = dbdata.NotificationResume.tail_estimated_cases(
                    geo_ids[d], 12
                )
            else:
                cases_series_last_12[d] = {}

        return dict(
            cities_alert=cities_alert,
            mun_dict=mun_dict,
            alerts=alerts,
            geo_ids=geo_ids,
            cases_series_last_12=cases_series_last_12,
        )

    def get_context_data(self, **kwargs):
        """
        :param kwargs:
        :return:
        """
        context = super().get_context_data(**kwargs)

        year_week = int(context["year_week"])
        year, week = context["year_week"][:4], context["year_week"][-2:]
        state = context["state"]
        state_name = STATE_NAME[state]

        regional_names = RegionalParameters.get_regional_names(state_name)

        diseases_key = ["dengue", "chik", "zika"]

        regional_info, last_year_week = self.get_regional_info(
            regional_names, state, year_week, diseases_key
        )

        last_year_week_s = str(last_year_week)
        last_year = last_year_week_s[:4]
        last_week = last_year_week_s[-2:]

        # map
        alerts_info = self.get_alerts_info(
            diseases_key,
            state,
            last_year_week,
        )

        context.update(
            {
                "year": year,
                "week": week,
                "last_year": last_year,
                "last_week": last_week,
                "state_name": state_name,
                "regional_info": regional_info,
                "regional_names": regional_names,
                "diseases_code": diseases_key,
                "diseases_name": ["Dengue", "Chikungunya", "Zika"],
                "mun_dict": alerts_info["mun_dict"],
                "geo_ids": alerts_info["geo_ids"],
                "alerts_level": alerts_info["alerts"],
                "case_series": alerts_info["cases_series_last_12"],
                "map_center": dbdata.MAP_CENTER[state],
                "map_zoom": dbdata.MAP_ZOOM[state],
            }
        )
        return context
