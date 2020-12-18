from collections import defaultdict, OrderedDict
import datetime
import fiona
import geojson
import json
import locale
import numpy as np
import os
import random


from django.apps import apps
from django.utils.translation import gettext as _
from django.shortcuts import redirect
from django.views.generic.base import TemplateView, View
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from time import mktime

# local
from . import dbdata, models as M
from .dbdata import (
    Forecast,
    MRJ_GEOCODE,
    CID10,
    ReportCity,
    ReportState,
    ALERT_COLOR,
    STATE_NAME,
    STATE_INITIAL,
)
from .episem import episem, episem2date
from .maps import get_city_info
from .models import City, RegionalHealth

from dados.charts.states import ReportStateCharts
from dados.charts.home import HomeCharts
from dados.charts.cities import ReportCityCharts, CityCharts

from gis.geotiff import convert_from_shapefile

DBF = apps.get_model('dbf', 'DBF')

locale.setlocale(locale.LC_TIME, locale="pt_BR.UTF-8")

dados_alerta = dbdata.get_alerta_mrj()
dados_alerta_chik = dbdata.get_alerta_mrj_chik()
dados_alerta_zika = dbdata.get_alerta_mrj_zika()

with open(os.path.join(settings.STATICFILES_DIRS[0], 'rio_aps.geojson')) as f:
    polygons = geojson.load(f)


def _get_disease_label(disease_code: str) -> str:
    return (
        'Dengue'
        if disease_code == 'dengue'
        else 'Chikungunya'
        if disease_code == 'chikungunya'
        else 'Zika'
        if disease_code == 'zika'
        else None
    )


def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(
        int(value[i : i + lv // 3], 16)  # noqa: E203
        for i in range(0, lv, lv // 3)
    )


def get_last_color_alert(geocode, disease, color_type='rgb'):
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
        '#cccccc',  # gray
        '#00ff00',  # green
        '#ffff00',  # yellow
        '#ff9900',  # orange
        '#ff0000',  # red
    ]

    if color_type == 'hex':
        return color_list[level]

    return hex_to_rgb(color_list[level])


def variation_p(v1, v2):
    return round(
        0
        if v1 == v2 == 0
        else ((v2 - v1) / 1) * 100
        if v1 == 0
        else ((v2 - v1) / v1) * 100,
        2,
    )


def get_alert(disease='dengue'):
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
        if disease == 'dengue'
        else dados_alerta_chik
        if disease == 'chikungunya'
        else dados_alerta_zika
        if disease == 'zika'
        else None
    )

    if df is None:
        raise Exception('Doença não cadastrada.')

    df = df.copy()
    df.fillna(0, inplace=True)

    last_SE = df.se.max()  # Last epidemiological week
    current = df[df['se'] == last_SE]  # Current status

    G = df.groupby("aps")
    alert = defaultdict(lambda: 0)
    case_series = {}  # estimated
    obs_case_series = {}
    min_max_est = {}
    last_year = None

    for ap in G.groups.keys():
        # .tail()  # only calculates on the series tail
        adf = G.get_group(ap).sort_values('data')

        k = str(float(ap.split('AP')[-1]))

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
    q = request.GET['q']
    muns = dbdata.get_city(q)
    data = json.dumps(
        [{'geocodigo': g, 'nome': n, 'uf': u} for g, n, u in muns]
    )
    return HttpResponse(data, content_type='application/json')


def load_series():
    """
    Monta as séries para visualização no site
    """
    series = defaultdict(lambda: defaultdict(lambda: []))
    G = dados_alerta.groupby("aps")
    for ap in G.groups.keys():
        series[ap]['dia'] = [
            int(mktime(datetime.datetime.strptime(d, "%Y-%m-%d").timetuple()))
            if isinstance(d, str)
            else None
            for d in G.get_group(ap).data
        ]
        series[ap]['tweets'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).tweets
        ]
        series[ap]['tmin'] = [
            float(i) if not np.isnan(i) else None for i in G.get_group(ap).tmin
        ]
        series[ap]['casos_est'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).casos_est
        ]
        series[ap]['casos'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).casos
        ]
        series[ap]['alerta'] = [
            c - 1 if not np.isnan(c) else None for c in G.get_group(ap).cor
        ]
    return series


class _GetMethod:
    """

    """

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
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super(AboutPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class ContactPageView(TemplateView):
    template_name = 'contact.html'

    def get_context_data(self, **kwargs):
        context = super(ContactPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class JoininPageView(TemplateView):
    template_name = 'joinin.html'

    def get_context_data(self, **kwargs):
        context = super(JoininPageView, self).get_context_data(**kwargs)
        # messages.info(
        #   self.request,
        #   'O site do projeto Alerta Dengue está em construção.')
        return context


class DataPublicServicesPageView(TemplateView):
    template_name = 'services.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        service = kwargs.get('service', None)
        service_type = (
            None if 'service_type' not in kwargs else kwargs['service_type']
        )

        if service == 'maps':
            if service_type is None:
                _static_root = os.path.abspath(settings.STATIC_ROOT)
                _static_dirs = os.path.abspath(settings.STATICFILES_DIRS[0])

                path_root = (
                    _static_root
                    if os.path.exists(_static_root)
                    else _static_dirs
                )

                geo_info_path = os.path.join(
                    path_root, 'geojson', 'geo_info.json'
                )

                with open(geo_info_path) as f:
                    geo_info_json = json.load(f)

                    context.update(
                        {
                            'geocodes': sorted(list(geo_info_json.keys())),
                            'mapserver_url': settings.MAPSERVER_URL,
                            'geo_info': geo_info_json,
                        }
                    )
                self.template_name = 'services_maps.html'
            else:
                self.template_name = 'services_maps_doc.html'
        elif service == 'tutorial':
            if service_type is None:
                self.template_name = 'services_tutorial.html'
            else:
                self.template_name = 'services_tutorial_R.html'
        elif service == 'api':
            if service_type is None:
                self.template_name = 'services_api.html'

                options_cities = ''
                for state_abbv, state_name in STATE_NAME.items():
                    for geocode, city_name in dbdata.get_cities(
                        state_name=state_name
                    ).items():
                        options_cities += '''
                        <option value="{0!s}">
                            {0!s} - {1!s} - {2!s}
                        </option>'''.format(
                            geocode, city_name.upper(), state_abbv
                        )

                dt_end = datetime.datetime.now()
                dt_start = dt_end - datetime.timedelta(weeks=4)

                yw_start = episem(dt_start, sep='')
                yw_end = episem(dt_end, sep='')

                dt_start_fmt = episem2date(yw_start, 1).strftime('%Y-%m-%d')
                dt_end_fmt = episem2date(yw_end, 1).strftime('%Y-%m-%d')

                context.update(
                    {
                        'options_cities': options_cities,
                        'date_query_start': dt_start_fmt,
                        'date_query_end': dt_end_fmt,
                    }
                )

                return context
            elif service_type == 'tutorialR':
                self.template_name = 'services_api_tutorialR.html'
            else:
                self.template_name = 'services_api_doc.html'
        else:
            self.template_name = 'services.html'

        return context


class AlertaMainView(TemplateView):
    template_name = 'main.html'

    _state_names = sorted(dbdata.STATE_NAME.values())
    _state_initials = {v: k for k, v in dbdata.STATE_NAME.items()}

    def get_context_data(self, **kwargs):
        context = super(AlertaMainView, self).get_context_data(**kwargs)

        diseases = tuple(dbdata.CID10.keys())

        n_alerts_chik = dbdata.get_n_chik_alerts()
        n_alerts_zika = dbdata.get_n_zika_alerts()

        # today
        last_se = {}

        case_series = defaultdict(dict)
        case_series_state = defaultdict(dict)

        count_cities = defaultdict(dict)
        current_week = defaultdict(dict)
        estimated_cases_next_week = defaultdict(dict)
        variation_to_current_week = defaultdict(dict)
        variation_4_weeks = defaultdict(dict)
        v1_week_fixed = defaultdict(dict)
        v1_4week_fixed = defaultdict(dict)

        notif_resume = dbdata.NotificationResume

        mundict = dict(dbdata.get_all_active_cities())
        # municipios, geocodigos = list(mundict.values()), list(mundict.keys())
        # results[d] = dbdata.load_serie_cities(geocodigos, d)
        for d in diseases:
            case_series[d] = dbdata.get_series_by_UF(d, 52)

            for s in self._state_names:
                df = case_series[d]  # alias
                df_state = df[df.uf == s]
                cases = df_state.casos_s.values

                # cases estimation
                cases_est = df_state.casos_est_s.values

                case_series_state[d][s] = cases[-52:]

                if d == 'dengue':
                    if not df_state.empty:
                        last_se[s] = df_state.tail(1).data.iloc[0]
                    else:
                        last_se[s] = ''

                count_cities[d][s] = notif_resume.count_cities_by_uf(s, d)
                current_week[d][s] = {
                    'casos': cases[-1] if cases.size else 0,
                    'casos_est': cases_est[-1] if cases_est.size else 0,
                }
                estimated_cases_next_week[d][s] = _('Em breve')
                v1 = 0 if not cases_est.size > 1 else cases_est[-2]
                v2 = 0 if not cases_est.size else cases_est[-1]

                v1_week_fixed[d][s] = v1 == 0 and v2 != 0

                variation_to_current_week[d][s] = variation_p(v1, v2)

                if cases_est.size < 55:
                    variation_4_weeks[d][s] = 0
                else:
                    v2 = cases_est[-4:-1].sum()
                    v1 = cases_est[-55:-52].sum()

                    v1_4week_fixed[d][s] = v1 == 0 and v2 != 0

                    variation_4_weeks[d][s] = variation_p(v1, v2)

        if n_alerts_chik > 0 and n_alerts_zika > 0:
            chart_cols = 4
            # card_cols = 6
        elif n_alerts_chik > 0 or n_alerts_zika > 0:
            chart_cols = 6
            # card_cols = 3
        else:
            chart_cols = 12
            # card_cols = 4

        # cheating
        card_cols = 6

        context.update(
            {
                # 'mundict': json.dumps(mundict),
                'num_mun': len(mundict),
                # 'municipios': municipios,
                # 'geocodigos': geocodigos,
                # 'alerta': json.dumps(alerta),
                'diseases': diseases,
                'case_series': case_series,
                # 'total': json.dumps(total.tolist()),
                'states': self._state_names,
                'count_cities': count_cities,
                'current_week': current_week,
                'estimated_cases_next_week': estimated_cases_next_week,
                'variation_to_current_week': variation_to_current_week,
                'variation_4_weeks': variation_4_weeks,
                'state_initials': self._state_initials,
                'n_alerts_chik': n_alerts_chik,
                'n_alerts_zika': n_alerts_zika,
                'last_se': last_se,
                'card_cols': card_cols,
                'chart_cols': chart_cols,
                # TODO: passar o df para o método que cria o chart
                #       gerar o gráfico referente ao dado
                #       atualmente apenas retorna um gráfico demo
                'chart_dengue': HomeCharts.create_dengue_chart({}),
                'chart_chik': HomeCharts.create_chik_chart({}),
                'chart_zika': HomeCharts.create_zika_chart({}),
            }
        )

        return context


class AlertCityPageBaseView(TemplateView, _GetMethod):
    pass


class AlertaMRJPageView(AlertCityPageBaseView):
    """
    Rio de Janeiro Alert View
    """

    template_name = 'alerta_mrj.html'

    def get_context_data(self, **kwargs):
        context = super(AlertaMRJPageView, self).get_context_data(**kwargs)

        disease_code = context['disease']

        disease_label = _get_disease_label(disease_code)

        bairros_mrj = {
            1.0: 'AP 1: Centro e adjacências',
            2.1: 'AP 2.1: Zona Sul',
            2.2: 'AP 2.2: Tijuca e adjacências',
            3.1: 'AP 3.1: Bonsucesso e adjacências',
            3.2: 'AP 3.2: Meier e adjacências',
            3.3: 'AP 3.3: Madureira e adjacências',
            4.0: 'AP 4: Barra, Recreio e Jacarepaguá',
            5.1: 'AP 5.1: Bangu e adjacências',
            5.2: 'AP 5.2: Campo Grande e adjacências',
            5.3: 'AP 5.3: Santa Cruz e adjacências',
        }

        geocode = str(MRJ_GEOCODE)

        city_info = get_city_info(geocode)

        # forecast epiweek reference
        forecast_date_min, forecast_date_max = Forecast.get_min_max_date(
            geocode=geocode, cid10=CID10[disease_code]
        )

        forecast_date_ref = self._get('ref', forecast_date_max)

        if forecast_date_ref is None:
            epiweek = None
        else:
            epiweek = episem(forecast_date_ref).replace('W', '')

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

                _ap = float(ap.split('AP')[-1])

                mask = current.aps == ap
                _v = int(current[mask]['casos_est'].values.astype(int)[0])

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
            city_chart = CityCharts.create_alert_chart(
                geocode,
                city_info['nome'],
                disease_label,
                disease_code,
                epiweek,
            )
        except ValueError:
            context = {
                'message': _(
                    "A doença {} não está registrada "
                    "em nosso banco de dados para o município de {}."
                ).format(disease_label, city_info['nome'])
            }
            self.template_name = 'error.html'
            return context

        context.update(
            {
                'geocodigo': geocode,  # legacy
                'geocode': geocode,
                'state_abv': 'RJ',
                'state': city_info['uf'],
                'nome': city_info['nome'],
                'populacao': city_info['populacao'],
                'incidencia': (
                    total_observed_series[-1] / city_info['populacao']
                )
                * 100000,  # casos/100000
                'casos_por_ap': json.dumps(casos_ap),
                'alerta': alerta,
                'novos_casos': sum(casos_ap.values()),
                'bairros': bairros_mrj,
                'min_est': sum(i[0] for i in min_max_est.values()),
                # 'min_est': sum(current.casos_estmin.values),
                'max_est': sum(i[1] for i in min_max_est.values()),
                # 'max_est': sum(current.casos_estmax.values),
                'series_casos': case_series,
                'SE': int(semana),
                'WEEK': str(semana),
                'yearweek': str(current.se.iat[0])[:],
                'data1': segunda.strftime("%d de %B de %Y"),
                'data2': (
                    segunda + datetime.timedelta(6)
                ),  # .strftime("%d de %B de %Y")
                'last_year': last_year,
                'look_back': len(total_series),
                'total_series': ', '.join(map(str, total_series)),
                'total_observed': total_observed_series[-1],
                'total_observed_series': ', '.join(
                    map(str, total_observed_series)
                ),
                'disease_label': disease_label,
                'disease_code': disease_code,
                'forecast_date_ref': forecast_date_ref,
                'forecast_date_min': forecast_date_min,
                'forecast_date_max': forecast_date_max,
                'epiweek': epiweek,
                'geojson_url': '/static/rio_aps.geojson',
                'chart_alert': city_chart,
            }
        )
        return context


class AlertaMunicipioPageView(AlertCityPageBaseView):
    template_name = 'alerta_municipio.html'

    def dispatch(self, request, *args, **kwargs):
        super(AlertaMunicipioPageView, self).get_context_data(**kwargs)

        geocode = kwargs['geocodigo']

        if int(geocode) == MRJ_GEOCODE:  # Rio de Janeiro
            return redirect('dados:mrj', disease='dengue', permanent=True)

        return super(AlertaMunicipioPageView, self).dispatch(
            request, *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = super(AlertaMunicipioPageView, self).get_context_data(
            **kwargs
        )

        disease_code = context['disease']

        disease_label = _get_disease_label(disease_code)

        geocode = context['geocodigo']

        city_info = get_city_info(geocode)

        # forecast epiweek reference
        forecast_date_min, forecast_date_max = Forecast.get_min_max_date(
            geocode=geocode, cid10=CID10[disease_code]
        )

        forecast_date_ref = self._get('ref', forecast_date_max)

        if forecast_date_ref is None:
            epiweek = None
        else:
            epiweek = episem(forecast_date_ref).replace('W', '')

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
            bairros = {geocode: city_info['nome']}
            total_series = case_series[-12:]
            total_observed_series = observed_cases[-12:]
        else:
            casos_ap = {}
            bairros = {}
            total_series = [0]
            total_observed_series = [0]

        try:
            city_chart = CityCharts.create_alert_chart(
                geocode,
                city_info['nome'],
                disease_label,
                disease_code,
                epiweek,
            )
        except ValueError:
            context = {
                'message': _(
                    "A doença {} não está registrada "
                    "em nosso banco de dados para o município de {}."
                ).format(disease_label, city_info['nome'])
            }
            self.template_name = 'error.html'
            return context

        context.update(
            {
                'geocodigo': geocode,  # legacy
                'geocode': geocode,
                'state': city_info['uf'],
                'state_abv': STATE_INITIAL[city_info['uf']],
                'nome': city_info['nome'],
                'populacao': city_info['populacao'],
                'incidencia': (case_series[-1] / city_info['populacao'])
                * 100000,  # casos/100000
                'casos_por_ap': json.dumps(casos_ap),
                'alerta': {geocode: alert},
                'prt1': prt1 * 100,
                'novos_casos': case_series[-1],
                'bairros': bairros,
                'min_est': min_max_est[0],
                'max_est': min_max_est[1],
                'series_casos': {geocode: case_series[-12:]},
                'SE': SE,
                'WEEK': str(SE)[4:],
                'data1': dia.strftime("%d de %B de %Y"),
                # .strftime("%d de %B de %Y")
                'data2': (dia + datetime.timedelta(6)),
                'last_year': last_year,
                'look_back': len(total_series),
                'total_series': ', '.join(map(str, total_series)),
                'total_observed': total_observed_series[-1],
                'total_observed_series': ', '.join(
                    map(str, total_observed_series)
                ),
                'disease_label': disease_label,
                'disease_code': disease_code,
                'forecast_date_ref': forecast_date_ref,
                'forecast_date_min': forecast_date_min,
                'forecast_date_max': forecast_date_max,
                'epiweek': epiweek,
                'geojson_url': '/static/geojson/%s.json' % geocode,
                'chart_alert': city_chart,
            }
        )
        return context


class AlertaGeoJSONView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(geojson.dumps(polygons))


class DetailsPageView(TemplateView):
    template_name = 'details.html'

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
            ga[k] = [1 if a == 0 else None for a in v['alerta']]
            ya[k] = [1 if a == 1 else None for a in v['alerta']]
            oa[k] = [1 if a == 2 else None for a in v['alerta']]
            ra[k] = [1 if a == 3 else None for a in v['alerta']]

        context.update(
            {
                'APS': aps,
                'green_alert': json.dumps(ga),
                'yellow_alert': json.dumps(ya),
                'casos': json.dumps(series),
                'red_alert': json.dumps(ra),
                'orange_alert': json.dumps(oa),
                'xvalues': series['AP1']['dia'],
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
                'O projeto conté dados apenas dos anos 2010 a 2013.',
            )

        sample = 1 if sample == 0 else sample / 100.0
        cases = "{\"type\":\"FeatureCollection\", \"features\":["
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
                "{\"type\":\"Feature\",\"geometry\":"
                + c.geojson
                + ", \"properties\":{\"data\":\""
                + c.dt_notific.isoformat()
                + "\"}},"
            )
        cases = cases[:-1] + "]}"
        # json.loads(cases)
        return HttpResponse(cases, content_type="application/json")


class AlertaStateView(TemplateView):
    template_name = 'state_cities.html'

    _state_name = dbdata.STATE_NAME

    _map_center = {
        'CE': [-05.069, -39.397],
        'ES': [-20.015, -40.803],
        'MG': [-18.542, -44.319],
        'PR': [-25.006, -51.833],
        'RJ': [-22.187, -43.176],
        'SP': [-23.5489, -46.6388],
        'RS': [-51.217699, -30.034632],
        'MA': [-2.53073, -44.3068],
    }
    _map_zoom = {
        'CE': 6,
        'ES': 6,
        'MG': 6,
        'PR': 6,
        'RJ': 6,
        'SP': 6,
        'RS': 6,
        'MA': 6,
    }

    def get_context_data(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        context = super(AlertaStateView, self).get_context_data(**kwargs)

        series_data_rj = None

        cities_alert = dbdata.NotificationResume.get_cities_alert_by_state(
            self._state_name[context['state']], context['disease']
        )

        alerts = dict(
            cities_alert[['municipio_geocodigo', 'level_alert']].values
        )

        mun_dict = dict(cities_alert[['municipio_geocodigo', 'nome']].values)
        is_just_rj = False

        if (
            not mun_dict
            and context['state'] == 'RJ'
            and context['disease'] == 'chikungunya'
        ):
            geo_id_rj = MRJ_GEOCODE
            mun_dict = {geo_id_rj: 'Rio de Janeiro'}
            series_data_rj = dbdata.load_series(geo_id_rj, 'chikungunya')[
                str(MRJ_GEOCODE)
            ]
            alerts = {str(geo_id_rj): series_data_rj['alerta'][-1]}
            is_just_rj = True

        mun_dict_ordered = OrderedDict(
            sorted(mun_dict.items(), key=lambda v: v[1])
        )

        geo_ids = list(mun_dict.keys())

        dbf = (
            DBF.objects.filter(state_abbreviation=context['state'])
            .order_by('export_date')
            .last()
        )

        if dbf is None:
            last_update = _('desconhecida')
        else:
            last_update = dbf.export_date

        if len(geo_ids) > 0:
            if not is_just_rj:
                cases_series_last_12 = dbdata.NotificationResume.tail_estimated_cases(  # noqa: E501
                    geo_ids, 12
                )
            else:
                cases_series_last_12 = {geo_id_rj: series_data_rj['casos_est']}
        else:
            cases_series_last_12 = {}

        context.update(
            {
                'state_abv': context['state'],
                'state': self._state_name[context['state']],
                'map_center': self._map_center[context['state']],
                'map_zoom': self._map_zoom[context['state']],
                'mun_dict': mun_dict,
                'mun_dict_ordered': mun_dict_ordered,
                'geo_ids': geo_ids,
                'alerts_level': alerts,
                # estimated cases is used to show a chart of the last 12 events
                'case_series': cases_series_last_12,
                'disease_label': context['disease'].title(),
                'last_update': last_update,
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
            shp_path = os.path.join(path, 'shapefile')

        shp = fiona.open(os.path.join(shp_path, '%s.shp' % geocode))

        result = convert_from_shapefile(
            shapefile=shp, rgb_color=get_last_color_alert(geocode, disease)
        )

        response = HttpResponse(
            result, content_type='application/force-download'
        )

        response['Content-Disposition'] = (
            'attachment; filename=%s.tiff' % geocode
        )

        return response


class GeoJsonView(View):
    """

    """

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
            geojson_path = os.path.join(path, 'geojson', '%s.json' % geocode)

        hex_color = get_last_color_alert(geocode, disease, color_type='hex')

        with open(geojson_path) as f:
            geojson_data = geojson.load(f)

        geojson_data['features'][0]['properties']['fill'] = hex_color
        result = geojson.dumps(geojson_data)

        response = HttpResponse(
            result, content_type='application/force-download'
        )

        response['Content-Disposition'] = (
            'attachment; filename=%s.json' % geocode
        )

        return response


class ReportView(TemplateView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.STATE_NAME = dict(STATE_NAME)
        # there are some cities from SP
        self.STATE_NAME.update({'SP': 'São Paulo'})

    def get_context_data(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        context = super().get_context_data(**kwargs)

        report_type = (
            context['report_type'] if 'report_type' in context else None
        )

        if report_type is None:
            context.update(self.view_filter_report_type(context))
        elif report_type == 'city':
            context.update(self.view_filter_city(context))
        else:
            context.update(self.view_filter_state(context))

        context.update({'disease_list': CID10})

        return context

    def view_filter_report_type(self, context):
        """

        :param context:
        :return:
        """
        self.template_name = 'report_filter_report_type.html'

        options_states = ''
        for state_initial, state_name in self.STATE_NAME.items():
            options_states += '''
            <option value="%(state_initial)s">
                %(state_name)s
            </option>''' % {
                'state_name': state_name,
                'state_initial': state_initial,
            }

        context.update({'options_states': options_states})

        return context

    def view_filter_city(self, context):
        """

        :param context:
        :return:
        """
        self.template_name = 'report_filter_city.html'

        options_cities = ''
        for geocode, city_name in dbdata.get_cities(
            state_name=self.STATE_NAME[context['state']]
        ).items():
            options_cities += '''
            <option value="%(geocode)s">
                %(city_name)s
            </option>''' % {
                'geocode': geocode,
                'city_name': city_name,
            }

        dt = datetime.datetime.now() - datetime.timedelta(days=7)
        yw = episem(dt, sep='')
        dt_fmt = episem2date(yw, 1).strftime('%Y-%m-%d')

        context.update(
            {'options_cities': options_cities, 'date_query': dt_fmt}
        )

        return context

    def view_filter_state(self, context):
        """

        :param context:
        :return:
        """
        self.template_name = 'report_filter_state.html'

        dt = datetime.datetime.now() - datetime.timedelta(days=7)
        yw = episem(dt, sep='')
        dt_fmt = episem2date(yw, 1).strftime('%Y-%m-%d')

        context.update({'date_query': dt_fmt})

        return context


class ReportCityView(TemplateView):
    template_name = 'report_city.html'

    def raise_error(self, context, message):
        """

        :return:
        """
        self.template_name = 'error.html'
        context.update({'message': message})
        return context

    def get_context_data(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        context = super(ReportCityView, self).get_context_data(**kwargs)

        geocode = int(context['geocode'])
        year_week = int(context['year_week'])
        year, week = context['year_week'][:4], context['year_week'][-2:]

        error_message_city_doesnt_exist = (
            'Esse municipio não participa do Infodengue. Se tiver '
            + 'interesse em aderir, contacte-nos pelo email '
            + ' <a href="mailto:alerta_dengue@fiocruz.br">'
            + 'alerta_dengue@fiocruz.br</a>'
        )

        city = City.objects.get(pk=int(geocode))

        try:
            regional_health = RegionalHealth.objects.get(
                municipio_geocodigo=int(geocode)
            )
        except Exception:
            return self.raise_error(context, error_message_city_doesnt_exist)

        station_id = regional_health.codigo_estacao_wu
        var_climate = regional_health.varcli
        u_crit = regional_health.ucrit
        t_crit = regional_health.tcrit
        threshold_pre_epidemic = regional_health.limiar_preseason
        threshold_pos_epidemic = regional_health.limiar_posseason
        threshold_epidemic = regional_health.limiar_epidemico

        climate_crit = None
        tweet_max = 0

        if var_climate.startswith('temp'):
            climate_crit = t_crit
            climate_title = 'Temperatura'
        elif var_climate.startswith('umid'):
            climate_crit = u_crit
            climate_title = 'Umidade'

        df_dengue = ReportCity.read_disease_data(
            geocode=geocode,
            disease_code=CID10['dengue'],
            station_id=station_id,
            year_week=year_week,
            var_climate=var_climate,
            has_tweets=True,
        )

        df_chik = ReportCity.read_disease_data(
            geocode=geocode,
            disease_code=CID10['chikungunya'],
            station_id=station_id,
            year_week=year_week,
            var_climate=var_climate,
            has_tweets=False,
        )

        df_zika = ReportCity.read_disease_data(
            geocode=geocode,
            disease_code=CID10['zika'],
            station_id=station_id,
            year_week=year_week,
            var_climate=var_climate,
            has_tweets=False,
        )

        # prepare empty variables
        chart_dengue_climate = ''
        chart_chik_climate = ''
        chart_chik_incidence = ''
        chart_zika_climate = ''
        chart_zika_incidence = ''

        total_n_dengue = 0
        total_n_dengue_last_year = 0
        total_n_chik = 0
        total_n_chik_last_year = 0
        total_n_zika = 0
        total_n_zika_last_year = 0

        last_year_week_l = []
        disease_last_code = []

        if not df_dengue.empty:
            last_year_week_l.append(df_dengue.index.max())

            chart_dengue_climate = ReportCityCharts.create_climate_chart(
                df=df_dengue,
                year_week=year_week,
                var_climate=var_climate,
                climate_crit=climate_crit,
                climate_title=climate_title,
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
            total_n_dengue = df_dengue[df_dengue.index // 100 == 2018][
                'casos notif.'
            ].sum()

            total_n_dengue_last_year = df_dengue[
                (df_dengue.index // 100 == year_week // 100 - 1)
                & (df_dengue.index <= year_week - 100)
            ]['casos notif.'].sum()

            tweet_max = np.nanmax(df_dengue.tweets)

        if not df_chik.empty:
            last_year_week_l.append(df_chik.index.max())

            chart_chik_climate = ReportCityCharts.create_climate_chart(
                df=df_chik,
                year_week=year_week,
                var_climate=var_climate,
                climate_crit=climate_crit,
                climate_title=climate_title,
            )

            chart_chik_incidence = ReportCityCharts.create_incidence_chart(
                df=df_chik,
                year_week=year_week,
                threshold_pre_epidemic=threshold_pre_epidemic,
                threshold_pos_epidemic=threshold_pos_epidemic,
                threshold_epidemic=threshold_epidemic,
            )

            total_n_chik = df_chik[df_chik.index // 100 == 2018][
                'casos notif.'
            ].sum()

            total_n_chik_last_year = df_chik[
                (df_chik.index // 100 == year_week // 100 - 1)
                & (df_chik.index <= year_week - 100)
            ]['casos notif.'].sum()

        if not df_zika.empty:
            last_year_week_l.append(df_zika.index.max())

            chart_zika_climate = ReportCityCharts.create_climate_chart(
                df=df_zika,
                year_week=year_week,
                var_climate=var_climate,
                climate_crit=climate_crit,
                climate_title=climate_title,
            )

            chart_zika_incidence = ReportCityCharts.create_incidence_chart(
                df=df_zika,
                year_week=year_week,
                threshold_pre_epidemic=threshold_pre_epidemic,
                threshold_pos_epidemic=threshold_pos_epidemic,
                threshold_epidemic=threshold_epidemic,
            )

            total_n_zika = df_zika[df_zika.index // 100 == 2018][
                'casos notif.'
            ].sum()

            total_n_zika_last_year = df_zika[
                (df_zika.index // 100 == year_week // 100 - 1)
                & (df_zika.index <= year_week - 100)
            ]['casos notif.'].sum()

        if not last_year_week_l:
            return self.raise_error(context, error_message_city_doesnt_exist)

        last_year_week = int(np.nanmax(last_year_week_l))

        for df in [df_dengue, df_chik, df_zika]:
            result = df[df.index == last_year_week]
            if not result.empty:
                disease_last_code.append(float(result['level_code']))

        max_alert_code = int(np.nanmax(disease_last_code))
        max_alert_color = ALERT_COLOR[max_alert_code]

        # param used by df.to_html
        html_param = dict(
            na_rep='',
            float_format=lambda x: ('%d' % x) if not np.isnan(x) else '',
            index=False,
            classes="table table-striped table-bordered",
        )

        prepare_html = (
            lambda df: df.iloc[-12:, :-2]
            .reset_index()
            .sort_values(by='SE', ascending=[False])
            .to_html(**html_param)
        )

        last_year_week_s = str(last_year_week)
        last_year = last_year_week_s[:4]
        last_week = last_year_week_s[-2:]

        context.update(
            {
                'year': year,
                'week': week,
                'last_year': last_year,
                'last_week': last_week,
                'city_name': city.name,
                'state_name': city.state,
                'df_dengue': prepare_html(df_dengue),
                'df_chik': prepare_html(df_chik),
                'df_zika': prepare_html(df_zika),
                'chart_dengue_climate': chart_dengue_climate,
                'chart_dengue_tweets': chart_dengue_tweets,
                'chart_dengue_incidence': chart_dengue_incidence,
                'chart_chik_climate': chart_chik_climate,
                'chart_chik_incidence': chart_chik_incidence,
                'chart_zika_climate': chart_zika_climate,
                'chart_zika_incidence': chart_zika_incidence,
                'total_n_dengue': total_n_dengue,
                'total_n_dengue_last_year': total_n_dengue_last_year,
                'total_n_chik': total_n_chik,
                'total_n_chik_last_year': total_n_chik_last_year,
                'total_n_zika': total_n_zika,
                'total_n_zika_last_year': total_n_zika_last_year,
                'max_alert_color': max_alert_color.title(),
                'tweet_max': tweet_max,
            }
        )
        return context


class ReportStateView(TemplateView):
    template_name = 'report_state.html'

    _map_center = {
        'CE': [-05.069, -39.397],
        'ES': [-20.015, -40.803],
        'MG': [-18.542, -44.319],
        'PR': [-25.006, -51.833],
        'RJ': [-22.187, -43.176],
        'SP': [-23.5489, -46.6388],
        'RS': [-51.217699, -30.034632],
        'MA': [-2.53073, -44.3068],
    }
    _map_zoom = {
        'CE': 6,
        'ES': 6,
        'MG': 6,
        'PR': 6,
        'RJ': 6,
        'SP': 6,
        'RS': 6,
        'MA': 6,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.STATE_NAME = dict(STATE_NAME)
        # there are some cities from SP
        self.STATE_NAME.update({'SP': 'São Paulo'})

    def raise_error(self, context, message):
        """

        :return:
        """
        self.template_name = 'error.html'
        context.update({'message': message})
        return context

    def prepare_html(self, df, var_climate):
        """

        :param df:
        :param var_climate:
        :return:
        """
        df['SE'] = df.index
        cols_to_sum = ['tweets'] + [
            'casos notif. dengue',
            'casos est. dengue',
            'casos notif. chik',
            'casos est. chik',
            'casos notif. zika',
            'casos est. zika',
        ]
        cols_to_avg = [var_climate.replace('_', '.')]

        df = df.groupby('SE')
        df = (
            df[cols_to_sum]
            .sum()
            .merge(
                df[cols_to_avg].aggregate(np.nanmean),
                how='outer',
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
            na_rep='',
            float_format=lambda x: ('%d' % x) if not np.isnan(x) else '',
            index=False,
            classes="datatables table table-striped table-bordered",
        )

        return (
            df.iloc[-6:, :]
            .replace(0, np.nan)
            .reset_index()
            .sort_values(by='SE', ascending=[False])
            .to_html(**html_param)
        )

    def get_context_data(self, **kwargs):
        """

        :param kwargs:
        :return:
        """
        context = super().get_context_data(**kwargs)

        year_week = int(context['year_week'])
        year, week = context['year_week'][:4], context['year_week'][-2:]
        state = context['state']

        regional_names = dbdata.get_regional_names(state)

        disease_key = ['dengue', 'chik', 'zika']

        regional_info = {}
        last_year_week = None

        for regional_name in regional_names:
            cities = dbdata.get_cities(
                state_name=self.STATE_NAME[state], regional_name=regional_name
            )

            station_id, var_climate = dbdata.get_var_climate_info(
                cities.keys()
            )

            df = ReportState.read_disease_data(
                year_week=year_week,
                cities=cities,
                station_id=station_id,
                var_climate=var_climate,
            )

            last_year_week_ = df.index.max()
            if last_year_week is None or last_year_week_ > last_year_week:
                last_year_week = last_year_week_

            cities_alert = {}
            chart_cases_twitter = {}

            for d in disease_key:
                try:
                    chart = ReportStateCharts.create_tweet_chart(
                        df=df, year_week=year_week, disease=d
                    )
                except Exception:
                    chart = '''
                    <br/>
                    <strong>Não há dados necessários para a geração do
                    gráfico sobre {}.
                    </strong>
                    <br/>
                    '''.format(
                        d
                    )

                chart_cases_twitter[d] = chart

            # each line refers to a city
            for i, row in df[df.index == last_year_week].iterrows():
                values = {}
                for d in disease_key:
                    values.update({d: row['level_code_{}'.format(d)]})
                cities_alert.update({row.geocode: values})

            regional_info.update(
                {
                    regional_name: {
                        'data': df,
                        'table': self.prepare_html(df, var_climate),
                        'cities_geocode': list(cities.keys()),
                        'cities_name': cities,
                        'cities_alert': cities_alert,
                        'chart_cases_twitter': chart_cases_twitter,
                    }
                }
            )

        last_year_week_s = str(last_year_week)
        last_year = last_year_week_s[:4]
        last_week = last_year_week_s[-2:]

        # map
        notif = dbdata.NotificationResume  # alias
        cities_alert = {}
        mun_dict = {}
        alerts = {}
        geo_ids = {}
        cases_series_last_12 = {}

        for d in disease_key:
            _d = d if d != 'chik' else 'chikungunya'

            cities_alert[d] = notif.get_cities_alert_by_state(
                state_name=self.STATE_NAME[state],
                disease=_d,
                epi_year_week=last_year_week,
            )

            alerts[d] = dict(
                cities_alert[d][['municipio_geocodigo', 'level_alert']].values
            )

            mun_dict[d] = dict(
                cities_alert[d][['municipio_geocodigo', 'nome']].values
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

        context.update(
            {
                'year': year,
                'week': week,
                'last_year': last_year,
                'last_week': last_week,
                'state_name': self.STATE_NAME[state],
                'regional_info': regional_info,
                'regional_names': regional_names,
                'diseases_code': ['dengue', 'chik', 'zika'],
                'diseases_name': ['Dengue', 'Chikungunya', 'Zika'],
                'mun_dict': mun_dict,
                'geo_ids': geo_ids,
                'alerts_level': alerts,
                'case_series': cases_series_last_12,
                'map_center': self._map_center[state],
                'map_zoom': self._map_zoom[state],
            }
        )
        return context
