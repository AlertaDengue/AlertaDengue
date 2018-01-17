# coding: utf-8
from django.apps import apps
from django.utils.translation import gettext
from django.shortcuts import redirect
from django.views.generic.base import TemplateView, View
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from time import mktime
from collections import defaultdict, OrderedDict
# local
from . import dbdata, models as M
from .dbdata import Forecast, MRJ_GEOCODE, CID10
from .episem import episem
from .maps import get_city_info
from gis.geotiff import convert_from_shapefile

import random
import fiona
import json
import os
import datetime
import numpy as np
import locale
import geojson


DBF = apps.get_model('dbf', 'DBF')

locale.setlocale(locale.LC_TIME, locale="pt_BR.UTF-8")

dados_alerta = dbdata.get_alerta_mrj()
dados_alerta_chik = dbdata.get_alerta_mrj_chik()
dados_alerta_zika = dbdata.get_alerta_mrj_zika()

with open(os.path.join(settings.STATICFILES_DIRS[0], 'rio_aps.geojson')) as f:
    polygons = geojson.load(f)


def _get_disease_label(disease_code: str) -> str:
    return (
        'Dengue' if disease_code == 'dengue' else
        'Chikungunya' if disease_code == 'chikungunya' else
        'Zika' if disease_code == 'zika' else
        None
    )


def hex_to_rgb(value):
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))


def get_last_color_alert(geocode, disease, color_type='rgb'):
    """

    :param geocode:
    :param disease:
    :param color_type: rba|hex
    :return:
    """
    df_level = dbdata.get_last_alert(geocode, disease)

    level = (
        0 if df_level.empty else
        0 if not (1 <= df_level.nivel[0] <= 4) else
        df_level.nivel[0]
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
        0 if v1 == v2 == 0 else
        ((v2 - v1) / 1) * 100 if v1 == 0 else
        ((v2 - v1) / v1) * 100, 2
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
        dados_alerta if disease == 'dengue' else
        dados_alerta_chik if disease == 'chikungunya' else
        dados_alerta_zika if disease == 'zika' else
        None
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

        case_series[k] = [
            int(v) for v in adf.casos_est.iloc[-12:].values
        ]
        obs_case_series[k] = [
            int(v) for v in adf.casos.iloc[-12:].values
        ]
        alert[ap] = adf.nivel.iloc[-1]
        last_year = int(adf.casos.iloc[-52])
        min_max_est[ap] = (
            adf.casos_estmin.iloc[-1],
            adf.casos_estmax.iloc[-1]
        )

    return alert, current, case_series, last_year, obs_case_series, min_max_est


def get_municipio(request):
    q = request.GET['q']
    muns = dbdata.get_city(q)
    data = json.dumps([
        {'geocodigo': g, 'nome': n, 'uf': u} for g, n, u in muns
    ])
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
            if isinstance(d, str) else None
            for d in G.get_group(ap).data
        ]
        series[ap]['tweets'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).tweets
        ]
        series[ap]['tmin'] = [
            float(i) if not np.isnan(i) else None
            for i in G.get_group(ap).tmin
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
            c - 1 if not np.isnan(c) else None
            for c in G.get_group(ap).cor
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
            self.request.GET[param]
            if param in self.request.GET else
            default
        )

        return result if result else default


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
            case_series[d] = dbdata.get_series_by_UF(d)

            for s in self._state_names:
                df = case_series[d]  # alias
                df_state = df[df.uf == s]
                cases = df_state.casos_s.values

                # cases estimation
                cases_est = df_state.casos_est_s.values

                case_series_state[d][s] = cases[:-52]

                if d == 'dengue':
                    if not df_state.empty:
                        last_se[s] = df_state.tail(1).data.iloc[0]
                    else:
                        last_se[s] = ''

                count_cities[d][s] = notif_resume.count_cities_by_uf(s, d)
                current_week[d][s] = {
                    'casos': cases[-1] if cases.size else 0,
                    'casos_est': cases_est[-1] if cases_est.size else 0
                }
                estimated_cases_next_week[d][s] = gettext('Em breve')
                v1 = cases_est[-2] if cases_est.size else 0
                v2 = cases_est[-1] if cases_est.size else 0

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

        context.update({
            # 'mundict': json.dumps(mundict),
            'num_mun': len(mundict),
            # 'municipios': municipios,
            # 'geocodigos': geocodigos,
            # 'alerta': json.dumps(alerta),
            'diseases': diseases,
            'case_series': case_series,
            #'total': json.dumps(total.tolist()),
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
            'chart_cols': chart_cols
        })

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
            5.3: 'AP 5.3: Santa Cruz e adjacências'
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

        alert, current, case_series, last_year, observed_cases, min_max_est = \
            get_alert(disease_code)

        if alert:
            casos_ap = {}
            alerta = {}

            for ap, v in alert.items():
                if ap not in current.aps:
                    continue

                _ap = float(ap.split('AP')[-1])

                mask = (current.aps == ap)
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

        context.update({
            'geocodigo': geocode,  # legacy
            'geocode': geocode,
            'nome': city_info['nome'],
            'populacao': city_info['populacao'],
            'incidencia': (
                total_observed_series[-1] / city_info['populacao']
            ) * 100000,  # casos/100000
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
            'data1': segunda.strftime("%d de %B de %Y"),
            'data2': (
                segunda + datetime.timedelta(6)
            ),  # .strftime("%d de %B de %Y")
            'last_year': last_year,
            'look_back': len(total_series),
            'total_series': ', '.join(map(str, total_series)),
            'total_observed': total_observed_series[-1],
            'total_observed_series': ', '.join(
                map(str, total_observed_series)),
            'disease_label': disease_label,
            'disease_code': disease_code,
            'forecast_date_ref': forecast_date_ref,
            'forecast_date_min': forecast_date_min,
            'forecast_date_max': forecast_date_max,
            'epiweek': epiweek,
            'geojson_url': '/static/rio_aps.geojson'
        })
        return context


class AlertaMunicipioPageView(AlertCityPageBaseView):
    template_name = 'alerta_municipio.html'

    def dispatch(self, request, *args, **kwargs):
        super(
            AlertaMunicipioPageView, self
        ).get_context_data(**kwargs)

        geocode = kwargs['geocodigo']

        if int(geocode) == MRJ_GEOCODE:  # Rio de Janeiro
            return redirect('dados:mrj', disease='dengue', permanent=True)

        return super(
            AlertaMunicipioPageView, self
        ).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AlertaMunicipioPageView, self) \
            .get_context_data(**kwargs)

        disease_code = context['disease']

        disease_label = _get_disease_label(disease_code)

        geocode = context['geocodigo']

        city_info = get_city_info(geocode)

        # forecast epiweek reference
        forecast_date_min, forecast_date_max = Forecast.get_min_max_date(
            geocode=geocode, cid10=CID10[disease_code]
        )

        forecast_date_ref = self._get(
            'ref', forecast_date_max
        )

        if forecast_date_ref is None:
            epiweek = None
        else:
            epiweek = episem(forecast_date_ref).replace('W', '')

        (
            alert, SE, case_series, last_year,
            observed_cases, min_max_est, dia, prt1
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

        context.update({
            'geocodigo': geocode, # legacy
            'geocode': geocode,
            'nome': city_info['nome'],
            'populacao': city_info['populacao'],
            'incidencia': (
                case_series[-1] / city_info['populacao']
            ) * 100000,  # casos/100000
            'casos_por_ap': json.dumps(casos_ap),
            'alerta': {geocode: alert},
            'prt1': prt1 * 100,
            'novos_casos': case_series[-1],
            'bairros': bairros,
            'min_est': min_max_est[0],
            'max_est': min_max_est[1],
            'series_casos': {geocode: case_series[-12:]},
            'SE': SE,
            'data1': dia.strftime("%d de %B de %Y"),
            # .strftime("%d de %B de %Y")
            'data2': (dia + datetime.timedelta(6)),
            'last_year': last_year,
            'look_back': len(total_series),
            'total_series': ', '.join(map(str, total_series)),
            'total_observed': total_observed_series[-1],
            'total_observed_series': ', '.join(
                map(str, total_observed_series)),
            'disease_label': disease_label,
            'disease_code': disease_code,
            'forecast_date_ref': forecast_date_ref,
            'forecast_date_min': forecast_date_min,
            'forecast_date_max': forecast_date_max,
            'epiweek': epiweek,
            'geojson_url': '/static/geojson/%s.json' % geocode
        })
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

        context.update({
            'APS': aps,
            'green_alert': json.dumps(ga),
            'yellow_alert': json.dumps(ya),
            'casos': json.dumps(series),
            'red_alert': json.dumps(ra),
            'orange_alert': json.dumps(oa),
            'xvalues': series['AP1']['dia'],
        })
        return context


class SinanCasesView(View):
    def get(self, request, year, sample):
        sample = int(sample)
        try:
            assert int(year) in [2010, 2011, 2012, 2013]
        except AssertionError:
            messages.error(
                self.request,
                'O projeto conté dados apenas dos anos 2010 a 2013.'
            )

        sample = 1 if sample == 0 else sample / 100.
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
                "{\"type\":\"Feature\",\"geometry\":" + c.geojson +
                ", \"properties\":{\"data\":\"" + c.dt_notific.isoformat() +
                "\"}},"
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
        'RJ': [-22.187, -43.176]
    }
    _map_zoom = {
        'CE': 6,
        'ES': 6,
        'MG': 6,
        'PR': 6,
        'RJ': 6
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
            not mun_dict and
            context['state'] == 'RJ' and
            context['disease'] == 'chikungunya'
        ):
            geo_id_rj = MRJ_GEOCODE
            mun_dict = {geo_id_rj: 'Rio de Janeiro'}
            series_data_rj = dbdata.load_series(
                geo_id_rj, 'chikungunya'
            )[str(MRJ_GEOCODE)]
            alerts = {str(geo_id_rj): series_data_rj['alerta'][-1]}
            is_just_rj = True

        mun_dict_ordered = OrderedDict(
            sorted(mun_dict.items(), key=lambda v: v[1])
        )

        geo_ids = list(mun_dict.keys())

        dbf = DBF.objects.filter(
            state_abbreviation=context['state']
        ).order_by('export_date').last()

        if dbf is None:
            last_update = gettext('desconhecida')
        else:
            last_update = dbf.export_date

        if len(geo_ids) > 0:
            if not is_just_rj:
                cases_series_last_12 = (
                    dbdata.NotificationResume.tail_estimated_cases(
                        geo_ids, 12
                    )
                )
            else:
                cases_series_last_12 = {
                    geo_id_rj: series_data_rj['casos_est']
                }
        else:
            cases_series_last_12 = {}

        context.update({
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
            'last_update': last_update
        })
        return context


class GeoTiffView(View):
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
            shp_path = os.path.join(path, 'shapefile')

        shp = fiona.open(os.path.join(shp_path, '%s.shp' % geocode))

        result = convert_from_shapefile(
            shapefile=shp,
            rgb_color=get_last_color_alert(geocode, disease)
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
